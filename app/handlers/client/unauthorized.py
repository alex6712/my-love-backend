from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.core.enums import APICode
from app.core.exceptions.auth import (
    IncorrectUsernameOrPasswordException,
    InvalidTokenException,
    TokenNotPassedException,
    TokenRevokedException,
    TokenSignatureExpiredException,
)
from app.main import my_love_backend
from app.schemas.v1.responses.standard import StandardResponse


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
