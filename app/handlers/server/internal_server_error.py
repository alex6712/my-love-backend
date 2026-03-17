from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.core.enums import APICode
from app.core.exceptions.auth import PasswordUpdateFailedException
from app.core.exceptions.base import UnexpectedStateException
from app.main import my_love_backend
from app.schemas.v1.responses.standard import StandardResponse


@my_love_backend.exception_handler(PasswordUpdateFailedException)
async def password_update_failed_exception_handler(
    request: Request,
    exc: PasswordUpdateFailedException,
) -> JSONResponse:
    """Обрабатывает исключения PasswordUpdateFailedException.

    Возвращает ошибку 500 Internal Server Error, если запрос на обновление
    пароля в БД не затронул ни одной строки.

    Parameters
    ----------
    request : Request
        Объект запроса с информацией о входящем HTTP-запросе (не используется).
    exc : PasswordUpdateFailedException
        Экземпляр исключения, из которого получаются данные для более точного ответа.

    Returns
    -------
    JSONResponse
        Ответ с ошибкой 500.
    """
    return JSONResponse(
        content=StandardResponse(
            code=APICode.PASSWORD_UPDATE_FAILED,
            detail=exc.detail,
        ).model_dump(mode="json"),
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


@my_love_backend.exception_handler(UnexpectedStateException)
async def unexpected_state_exception_handler(
    request: Request,
    exc: UnexpectedStateException,
) -> JSONResponse:
    """Обрабатывает исключения UnexpectedStateException.

    Универсальный обработчик для неожиданных состояний системы, которые не должны
    возникать при нормальной работе. Возвращает ответ с кодом 500 и общим сообщением,
    чтобы не раскрывать внутренние детали ошибки.

    Parameters
    ----------
    request : Request
        Объект входящего HTTP-запроса (не используется).
    exc : UnexpectedStateException
        Экземпляр исключения (детали ошибки логируются отдельно, в ответ не попадают).

    Returns
    -------
    JSONResponse
        Ответ с HTTP-статусом 500 Internal Server Error и телом в формате StandardResponse,
        где code = APICode.INTERNAL_SERVER_ERROR, detail - общее сообщение об ошибке.
    """
    return JSONResponse(
        content=StandardResponse(
            code=APICode.INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred.",
        ).model_dump(mode="json"),
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
