from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from botocore.exceptions import ClientError
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1 import api_v1_router
from app.config import Settings, get_settings
from app.core.enums import APICode
from app.core.exceptions.auth import (
    CredentialsException,
    CredentialsType,
    TokenNotPassedException,
    TokenRevokedException,
)
from app.core.exceptions.base import AlreadyExistsException, NotFoundException
from app.core.exceptions.couple import CoupleNotSelfException
from app.core.exceptions.media import UnsupportedFileTypeException
from app.infrastructure.postgresql import async_postgresql_engine
from app.infrastructure.redis import redis_client
from app.infrastructure.s3 import get_s3_client
from app.schemas.v1.responses.standard import StandardResponse

settings: Settings = get_settings()

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
        "name": "media",
        "description": "Операции с **медиа** в приложении.",
    },
]


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, Any]:
    """Менеджер срока службы FastAPI-приложения.

    Используется для менеджмента самого приложения в процессе
    его работы.

    В данном случае выполняет следующие действия:
    - Инициализирует бакет MinIO через клиент `aioboto3`;
    - Создаёт пул подключений к Redis.

    Parameters
    ----------
    _ : FastAPI
        Объект приложения для менеджмента (не используется).

    Yields
    ------
    None
        При успешном выполнении ничего не возвращает.
    """
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

my_love_backend.include_router(api_v1_router)


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


@my_love_backend.exception_handler(CredentialsException)
async def credentials_exception_handler(
    request: Request,
    exc: CredentialsException,
) -> JSONResponse:
    """Обрабатывает исключения CredentialsException.

    Возвращает ошибку 401 Not Authorized при проблемах с предоставленными
    учётными данными (будь это пароль или токен).

    Parameters
    ----------
    request : Request
        Объект запроса с информацией о входящем HTTP-запросе (не используется).
    exc : CredentialsException
        Экземпляр исключения, из которого получаются данные для более точного ответа.

    Returns
    -------
    JSONResponse
        Ответ с ошибкой 401.
    """
    type_to_code: dict[CredentialsType, APICode] = {
        "password": APICode.INCORRECT_USERNAME_PASSWORD,
        "token": APICode.INCORRECT_TOKEN,
    }

    code: APICode = type_to_code[exc.credentials_type]
    if exc.detail == "Signature of passed token has expired.":
        code = APICode.TOKEN_SIGNATURE_EXPIRED

    return JSONResponse(
        content=StandardResponse(
            code=code,
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
    return JSONResponse(
        content=StandardResponse(
            code=APICode.RESOURCE_NOT_FOUND,
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
