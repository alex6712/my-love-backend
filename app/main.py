from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, cast

from botocore.exceptions import ClientError
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import (
    get_openapi,
    validation_error_definition,  # type: ignore
)
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.root import api_root_router
from app.api.v1 import api_v1_router
from app.config import get_settings
from app.core.docs import (
    AUTHORIZATION_ERROR_SCHEMA,
    IDEMPOTENCY_CONFLICT_ERROR_SCHEMA,
    LOGIN_ERROR_SCHEMA,
    RATE_LIMIT_ERROR_SCHEMA,
    REGISTER_ERROR_SCHEMA,
)
from app.core.enums import APICode
from app.core.exceptions.auth import (
    IncorrectUsernameOrPasswordException,
    InvalidTokenException,
    TokenNotPassedException,
    TokenRevokedException,
    TokenSignatureExpiredException,
)
from app.core.exceptions.base import (
    AlreadyExistsException,
    IdempotencyException,
    NotFoundException,
)
from app.core.exceptions.couple import CoupleNotSelfException
from app.core.exceptions.media import (
    MediaNotFoundException,
    UnsupportedFileTypeException,
    UploadNotCompletedException,
)
from app.core.rate_limiter import limiter
from app.infrastructure.postgresql import async_postgresql_engine
from app.infrastructure.redis import redis_client
from app.infrastructure.s3 import get_s3_client
from app.schemas.v1.responses.standard import StandardResponse
from app.schemas.v1.responses.validation_error import ValidationErrorResponse

settings = get_settings()

tags_metadata = [
    {
        "name": "root",
        "description": "Получение информации о **приложении**.",
    },
    {
        "name": "authorization",
        "description": "Операции **регистрации** и **аутентификации**.",
    },
    {
        "name": "couples",
        "description": "Операции с **парами** между пользователями приложения.",
    },
    {
        "name": "users",
        "description": "Операции с **пользователями** приложения.",
    },
    {
        "name": "media-files",
        "description": "Операции с **медиа-файлами**: загрузка, скачивание, presigned URLs.",
    },
    {
        "name": "media-albums",
        "description": "Операции с **медиа-альбомами**: создание, получение, привязка файлов.",
    },
    {
        "name": "notes",
        "description": "Операции с пользовательскими **заметками**.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, Any]:
    """Менеджер срока службы FastAPI-приложения.

    Используется для менеджмента самого приложения в процессе
    его работы.

    В данном случае выполняет следующие действия:
    - Инициализирует бакет MinIO через клиент `aioboto3`;
    - Создаёт пул подключений к Redis.

    Parameters
    ----------
    app : FastAPI
        Объект приложения для менеджмента.

    Yields
    ------
    None
        При успешном выполнении ничего не возвращает.
    """
    app.state.startup_at = datetime.now(timezone.utc)
    app.state.limiter = limiter

    async with get_s3_client() as s3_client:
        try:
            await s3_client.head_bucket(Bucket=settings.MINIO_BUCKET_NAME)
        except ClientError as e:
            error_code: str = e.response.get("Error", {}).get("Code", "")

            if error_code in ("404", "NoSuchBucket"):
                await s3_client.create_bucket(Bucket=settings.MINIO_BUCKET_NAME)
            else:
                raise

    await redis_client.connect()

    yield

    await async_postgresql_engine.dispose()

    await redis_client.disconnect()


my_love_backend = FastAPI(
    title=settings.APP_NAME,
    summary=settings.APP_SUMMARY,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    openapi_tags=tags_metadata,
    lifespan=lifespan,
    contact={
        "name": settings.ADMIN_NAME,
        "email": settings.ADMIN_EMAIL,
    },
)

my_love_backend.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

my_love_backend.include_router(api_root_router)
my_love_backend.include_router(api_v1_router)


def custom_openapi() -> dict[str, Any]:
    """Генерирует и возвращает кастомную схему OpenAPI для FastAPI приложения.

    Функция реализует паттерн кэширования (singleton-like) для схемы OpenAPI.
    При первом вызове генерирует полную схему на основе конфигурации приложения,
    добавляет кастомные компоненты ответов и сохраняет результат в кэше.
    Последующие вызовы возвращают кэшированную схему.

    Returns
    -------
    dict[str, Any]
        Словарь со схемой OpenAPI в формате JSON, содержащий.

    Notes
    -----
    Схема включает стандартные компоненты FastAPI, дополненные кастомными
    ошибками для различных сценариев:
    - AuthorizationError: Ошибки авторизации;
    - LoginError: Ошибки аутентификации;
    - RateLimitError: Превышение лимитов запросов;
    - RegisterError: Ошибки регистрации.

    Все настройки (название, версия, контакты) берутся из объекта `settings`.
    """
    if my_love_backend.openapi_schema:
        return my_love_backend.openapi_schema

    openapi_schema = get_openapi(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        summary=settings.APP_SUMMARY,
        description=settings.APP_DESCRIPTION,
        routes=my_love_backend.routes,
        tags=tags_metadata,
        contact={
            "name": settings.ADMIN_NAME,
            "email": settings.ADMIN_EMAIL,
        },
    )

    openapi_schema["components"]["responses"] = {
        "AuthorizationError": AUTHORIZATION_ERROR_SCHEMA,
        "IdempotencyConflictError": IDEMPOTENCY_CONFLICT_ERROR_SCHEMA,
        "LoginError": LOGIN_ERROR_SCHEMA,
        "RateLimitError": RATE_LIMIT_ERROR_SCHEMA,
        "RegisterError": REGISTER_ERROR_SCHEMA,
    }

    for path in openapi_schema["paths"].values():
        for method in path.values():
            if not (responses := method.get("responses", None)):
                continue

            if not responses.get("422", None):
                continue

            schema = ValidationErrorResponse.model_json_schema(
                ref_template="#/components/schemas/{model}",
            )
            _ = schema.pop("$defs")

            responses["422"] = {
                "description": "Ошибка валидации",
                "content": {"application/json": {"schema": schema}},
            }

    _ = openapi_schema["components"]["schemas"].pop("HTTPValidationError", None)
    _ = openapi_schema["components"]["schemas"].pop("ValidationError", None)

    openapi_schema["components"]["schemas"]["ErrorDetails"] = (
        validation_error_definition
    )

    my_love_backend.openapi_schema = openapi_schema
    return my_love_backend.openapi_schema


my_love_backend.openapi = custom_openapi


@my_love_backend.exception_handler(status.HTTP_404_NOT_FOUND)
async def not_found_exception_handler(
    request: Request,
    _: StarletteHTTPException,
) -> JSONResponse:
    """Обрабатывает HTTP исключения с кодом 404.

    Обработчик исключений на доступ к неизвестному ресурсу.

    Parameters
    ----------
    request : Request
        Объект HTTP-запроса для инъекции пути (не используется).
    _ : StarletteHTTPException
        Экземпляр исключения (не используется).

    Returns
    -------
    JSONResponse
        Ответ с ошибкой 404.
    """
    return JSONResponse(
        content=StandardResponse(
            code=APICode.RESOURCE_NOT_FOUND,
            detail="Resource you're looking not exists or you're lack of rights.",
        ).model_dump(mode="json"),
        status_code=status.HTTP_404_NOT_FOUND,
    )


@my_love_backend.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """
    Docstring for request_validation_error_handler

    :param request: Description
    :type request: Request
    :param exc: Description
    :type exc: RequestValidationError
    :return: Description
    :rtype: JSONResponse
    """
    return JSONResponse(
        content=ValidationErrorResponse(
            code=APICode.VALIDATION_ERROR,
            detail=jsonable_encoder(exc.errors()),
        ).model_dump(mode="json"),
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )


@my_love_backend.exception_handler(RateLimitExceeded)
async def rate_limit_exception_handler(
    request: Request,
    exc: RateLimitExceeded,
) -> JSONResponse:
    """Обрабатывает ошибки rate limiting (429 Too Many Requests).

    Возвращает клиенту стандартизированный ответ с ошибкой 429
    и рекомендуемым заголовком Retry-After.

    Parameters
    ----------
    request : Request
        Объект запроса с информацией о входящем HTTP-запросе.
    exc : RateLimitExceeded
        Исключение, вызвавшее ошибку 429 (не используется).

    Returns
    -------
    JSONResponse
        Ответ с ошибкой 429, кодом RATE_LIMIT_EXCEEDED.
    """
    response = JSONResponse(
        content=StandardResponse(
            code=APICode.RATE_LIMIT_EXCEEDED,
            detail="Too many requests. Please slow down.",
        ).model_dump(mode="json"),
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
    )

    request.app.state.limiter._inject_headers(response, request.state.view_rate_limit)

    return response


@my_love_backend.exception_handler(IncorrectUsernameOrPasswordException)
async def incorrect_username_or_password_exception_handler(
    request: Request,
    exc: IncorrectUsernameOrPasswordException,
) -> JSONResponse:
    """Обрабатывает исключения IncorrectUsernameOrPasswordException.

    Возвращает ошибку 401 Not Authorized при проблемах с предоставленными
    учётными данными при логине.

    Parameters
    ----------
    request : Request
        Объект запроса с информацией о входящем HTTP-запросе (не используется).
    exc : IncorrectUsernameOrPasswordException
        Экземпляр исключения, из которого получаются данные для более точного ответа.

    Returns
    -------
    JSONResponse
        Ответ с ошибкой 401.
    """
    return JSONResponse(
        content=StandardResponse(
            code=APICode.INCORRECT_USERNAME_PASSWORD,
            detail=exc.detail,
        ).model_dump(mode="json"),
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


@my_love_backend.exception_handler(TokenNotPassedException)
async def token_not_passed_exception_handler(
    request: Request,
    exc: TokenNotPassedException,
) -> JSONResponse:
    """Обрабатывает исключения TokenNotPassedException.

    Специализированный обработчик для случаев отсутствия токена в заголовках запроса.

    Parameters
    ----------
    request : Request
        Объект входящего HTTP-запроса (не используется).
    exc : TokenNotPassedException
        Экземпляр исключения с дополнительными атрибутами:
        - token_type: str - тип отсутствующего токена (например, 'access')

    Returns
    -------
    JSONResponse
        Ответ с указанием типа отсутствующего токен.
    """
    return JSONResponse(
        content=StandardResponse(
            code=APICode.TOKEN_NOT_PASSED,
            detail=exc.detail,
        ).model_dump(mode="json"),
        status_code=status.HTTP_401_UNAUTHORIZED,
        headers={"WWW-Authenticate": "Bearer"},
    )


@my_love_backend.exception_handler(TokenRevokedException)
async def token_revoked_exception_handler(
    request: Request,
    exc: TokenRevokedException,
) -> JSONResponse:
    """Обрабатывает исключения TokenRevokedException.

    Специализированный обработчик для случаев использования отозванного токена.

    Parameters
    ----------
    request : Request
        Объект входящего HTTP-запроса (не используется).
    exc : TokenRevokedException
        Объект исключения с информацией о токене.

    Returns
    -------
    JSONResponse
        Ответ с ошибкой 401.
    """
    return JSONResponse(
        content=StandardResponse(
            code=APICode.TOKEN_REVOKED,
            detail=exc.detail,
        ).model_dump(mode="json"),
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


@my_love_backend.exception_handler(InvalidTokenException)
async def invalid_token_exception_handler(
    request: Request,
    exc: InvalidTokenException,
) -> JSONResponse:
    """Обрабатывает исключения InvalidTokenException.

    Возвращает ошибку 401 Not Authorized при проблемах с проверкой
    подписи переданного токена.

    Parameters
    ----------
    request : Request
        Объект запроса с информацией о входящем HTTP-запросе (не используется).
    exc : IncorrectUsernameOrPasswordException
        Экземпляр исключения, из которого получаются данные для более точного ответа.

    Returns
    -------
    JSONResponse
        Ответ с ошибкой 401.
    """
    return JSONResponse(
        content=StandardResponse(
            code=APICode.INVALID_TOKEN,
            detail=exc.detail,
        ).model_dump(mode="json"),
        status_code=status.HTTP_401_UNAUTHORIZED,
        headers={"WWW-Authenticate": "Bearer"},
    )


@my_love_backend.exception_handler(TokenSignatureExpiredException)
async def token_signature_expired_exception_handler(
    request: Request,
    exc: TokenSignatureExpiredException,
) -> JSONResponse:
    """Обрабатывает исключения TokenSignatureExpiredException.

    Возвращает ошибку 401 Not Authorized, если подпись переданного клиентом
    токена верна, однако просрочена.

    Parameters
    ----------
    request : Request
        Объект запроса с информацией о входящем HTTP-запросе (не используется).
    exc : IncorrectUsernameOrPasswordException
        Экземпляр исключения, из которого получаются данные для более точного ответа.

    Returns
    -------
    JSONResponse
        Ответ с ошибкой 401.
    """
    return JSONResponse(
        content=StandardResponse(
            code=APICode.TOKEN_SIGNATURE_EXPIRED,
            detail=exc.detail,
        ).model_dump(mode="json"),
        status_code=status.HTTP_401_UNAUTHORIZED,
        headers={"WWW-Authenticate": "Bearer"},
    )


@my_love_backend.exception_handler(NotFoundException)
async def domain_not_found_exception_handler(
    request: Request,
    exc: NotFoundException,
) -> JSONResponse:
    """Обрабатывает исключения NotFoundException.

    Возвращает клиенту ответ с HTTP 404 в случае, если пользователь
    предоставил некорректные данные для поиска записи.

    Parameters
    ----------
    request : Request
        Объект запроса FastAPI, содержащий информацию о входящем HTTP-запросе (не используется).
    exc : NotFoundException
        Экземпляр исключения, из которого получаются данные для более точного ответа.

    Returns
    -------
    JSONResponse
        Ответ с ошибкой 404.
    """
    code = APICode.RESOURCE_NOT_FOUND

    match exc.domain:
        case "media":
            media_exc = cast(MediaNotFoundException, exc)

            match media_exc.media_type:
                case "album":
                    code = APICode.ALBUM_NOT_FOUND
                case "file":
                    code = APICode.FILE_NOT_FOUND
                case _:
                    pass
        case _:
            pass

    return JSONResponse(
        content=StandardResponse(
            code=code,
            detail=exc.detail,
        ).model_dump(mode="json"),
        status_code=status.HTTP_404_NOT_FOUND,
    )


@my_love_backend.exception_handler(AlreadyExistsException)
async def username_already_exists_exception_handler(
    request: Request,
    exc: AlreadyExistsException,
) -> JSONResponse:
    """Обрабатывает исключения AlreadyExistsException.

    Возвращает клиенту ответ с HTTP 409 в случае, если зафиксирована
    попытка регистрации новой записи с нарушением отношения уникальности.

    Parameters
    ----------
    request : Request
        Объект запроса FastAPI, содержащий информацию о входящем HTTP-запросе (не используется).
    exc : AlreadyExistsException
        Экземпляр исключения, из которого получаются данные для более точного ответа.

    Returns
    -------
    JSONResponse
        Ответ с ошибкой 409.
    """
    return JSONResponse(
        content=StandardResponse(
            code=APICode.UNIQUE_CONFLICT,
            detail=exc.detail,
        ).model_dump(mode="json"),
        status_code=status.HTTP_409_CONFLICT,
    )


@my_love_backend.exception_handler(CoupleNotSelfException)
async def couple_not_self_exception_handler(
    request: Request,
    exc: CoupleNotSelfException,
) -> JSONResponse:
    """Обрабатывает исключения CoupleNotSelfException.

    Возвращает клиенту ответ с HTTP 400 в случае, если зафиксирована
    попытка регистрации новой пары пользователей, при этом переданы
    совпадающие UUID.

    Parameters
    ----------
    request : Request
        Объект запроса FastAPI, содержащий информацию о входящем HTTP-запросе (не используется).
    exc : CoupleNotSelfException
        Экземпляр исключения, из которого получаются данные для более точного ответа.

    Returns
    -------
    JSONResponse
        Ответ с ошибкой 400.
    """
    return JSONResponse(
        content=StandardResponse(
            code=APICode.COUPLE_NOT_SELF,
            detail=exc.detail,
        ).model_dump(mode="json"),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


@my_love_backend.exception_handler(UnsupportedFileTypeException)
async def unsupported_file_type_exception_handler(
    request: Request,
    exc: UnsupportedFileTypeException,
) -> JSONResponse:
    """Обрабатывает исключения UnsupportedFileTypeException.

    Возвращает клиенту ответ с HTTP 400 в случае, если зафиксирована
    попытка загрузки файла с необрабатываемым типом.

    Parameters
    ----------
    request : Request
        Объект запроса FastAPI, содержащий информацию о входящем HTTP-запросе (не используется).
    exc : UnsupportedFileTypeException
        Экземпляр исключения, из которого получаются данные для более точного ответа.

    Returns
    -------
    JSONResponse
        Ответ с ошибкой 400.
    """
    return JSONResponse(
        content=StandardResponse(
            code=APICode.UNSUPPORTED_FILE_TYPE,
            detail=exc.detail,
        ).model_dump(mode="json"),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


@my_love_backend.exception_handler(UploadNotCompletedException)
async def upload_not_completed_exception_handler(
    request: Request,
    exc: UploadNotCompletedException,
) -> JSONResponse:
    """Обрабатывает исключения UploadNotCompletedException.

    Возвращает клиенту ответ с HTTP 404 в случае, если при
    подтверждении окончания клиентом загрузки файла,
    в объектом хранилище файл не найден.

    Parameters
    ----------
    request : Request
        Объект запроса FastAPI, содержащий информацию о входящем HTTP-запросе (не используется).
    exc : UploadNotCompletedException
        Экземпляр исключения, из которого получаются данные для более точного ответа.

    Returns
    -------
    JSONResponse
        Ответ с ошибкой 404.
    """
    return JSONResponse(
        content=StandardResponse(
            code=APICode.UPLOAD_NOT_COMPLETED,
            detail=exc.detail,
        ).model_dump(mode="json"),
        status_code=status.HTTP_404_NOT_FOUND,
    )


@my_love_backend.exception_handler(IdempotencyException)
async def idempotency_exception_handler(
    request: Request,
    exc: IdempotencyException,
) -> JSONResponse:
    """Обрабатывает исключения IdempotencyException.

    Специализированный обработчик для случаев, когда по переданному ключу
    идемпотентности обработка запроса уже начата.

    Parameters
    ----------
    request : Request
        Объект входящего HTTP-запроса (не используется).
    exc : IdempotencyException
        Экземпляр исключения для предоставления более детального сообщения об ошибке.

    Returns
    -------
    JSONResponse
        Ответ с указанием на то, что запрос уже в обработке.
    """
    return JSONResponse(
        content=StandardResponse(
            code=APICode.IDEMPOTENCY_CONFLICT,
            detail=exc.detail,
        ).model_dump(mode="json"),
        status_code=status.HTTP_409_CONFLICT,
    )
