from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1 import api_v1_router
from app.config import Settings, get_settings
from app.core.exceptions import (
    CredentialsException,
    TokenNotPassedException,
    TokenRevokedException,
    UserNotFoundException,
    UsernameAlreadyExistsException,
)

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
]

my_love_backend = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    summary=settings.APP_SUMMARY,
    contact={
        "name": settings.ADMIN_NAME,
        "email": settings.ADMIN_EMAIL,
    },
    openapi_tags=tags_metadata,
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
        content={
            "detail": "Resource you're looking not exists or you're lack of rights.",
        },
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
    _ : CredentialsException
        Экземпляр исключения (не используется).

    Returns
    -------
    JSONResponse
        Ответ с ошибкой 401.
    """
    details: dict[str, str] = {
        "password": "Incorrect username or password.",
        "token": str(exc),
    }

    return JSONResponse(
        content={"detail": details.get(exc.credentials_type)},
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
        content={
            "detail": f"{exc.token_type.capitalize()} token is missing in headers.",
        },
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
        content={
            "detail": "Access token has been revoked.",
        },
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


@my_love_backend.exception_handler(UserNotFoundException)
async def user_not_found_exception_handler(
    request: Request,
    _: UserNotFoundException,
) -> JSONResponse:
    """Обрабатывает исключения UserNotFoundException.

    Возвращает клиенту ответ с HTTP 401 в случае, если пользователь
    предоставил некорректное имя пользователя `username`.

    Parameters
    ----------
    request : Request
        Объект запроса FastAPI, содержащий информацию о входящем HTTP-запросе (не используется).
    _ : UserNotFoundException
        Экземпляр вызванного исключения (не используется).

    Returns
    -------
    JSONResponse
        Ответ с ошибкой 401.
    """
    return JSONResponse(
        content={"detail": "Incorrect username or password."},
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


@my_love_backend.exception_handler(UsernameAlreadyExistsException)
async def username_already_exists_exception_handler(
    request: Request,
    _: UsernameAlreadyExistsException,
) -> JSONResponse:
    """Обрабатывает исключения UsernameAlreadyExistsException.

    Возвращает клиенту ответ с HTTP 409 в случае, если зафиксирована
    попытка регистрации нового пользователя с уже существующим `username`.

    Parameters
    ----------
    request : Request
        Объект запроса FastAPI, содержащий информацию о входящем HTTP-запросе (не используется).
    _ : UserNotFoundException
        Экземпляр вызванного исключения (не используется).

    Returns
    -------
    JSONResponse
        Ответ с ошибкой 409.
    """
    return JSONResponse(
        content={"detail": "Username already exists."},
        status_code=status.HTTP_409_CONFLICT,
    )
