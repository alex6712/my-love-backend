from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.core.enums import APICode
from app.core.exceptions.base import NothingToUpdateException
from app.core.exceptions.couple import CoupleNotSelfException
from app.core.exceptions.media import UnsupportedFileTypeException
from app.main import my_love_backend
from app.schemas.v1.responses.standard import StandardResponse


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


@my_love_backend.exception_handler(NothingToUpdateException)
async def nothing_to_update_exception_handler(
    request: Request,
    exc: NothingToUpdateException,
) -> JSONResponse:
    """Обрабатывает исключения NothingToUpdateException.

    Специализированный обработчик для случаев, когда PATCH-запрос
    не содержит ни одного поля для обновления.

    Parameters
    ----------
    request : Request
        Объект входящего HTTP-запроса (не используется).
    exc : NothingToUpdateException
        Экземпляр исключения с детальным описанием ошибки.

    Returns
    -------
    JSONResponse
        Ответ с указанием на то, что в запросе отсутствуют данные для обновления.
    """
    return JSONResponse(
        content=StandardResponse(
            code=APICode.NOTHING_TO_UPDATE,
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
