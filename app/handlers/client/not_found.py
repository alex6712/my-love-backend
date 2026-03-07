from typing import cast

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.enums import APICode
from app.core.exceptions.base import NotFoundException
from app.core.exceptions.media import (
    MediaNotFoundException,
    UploadNotCompletedException,
)
from app.main import my_love_backend
from app.schemas.v1.responses.standard import StandardResponse


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
