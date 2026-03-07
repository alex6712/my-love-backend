from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.core.enums import APICode
from app.core.exceptions.media import FileUploadPendingException
from app.main import my_love_backend
from app.schemas.v1.responses.standard import StandardResponse


@my_love_backend.exception_handler(FileUploadPendingException)
async def file_upload_pending_exception_handler(
    request: Request,
    exc: FileUploadPendingException,
) -> JSONResponse:
    """Обрабатывает исключения FileUploadPendingException.

    Возвращает клиенту ответ с HTTP 202 в случае, если запрошенный файл
    ещё не завершил загрузку в хранилище (статус PENDING).

    Parameters
    ----------
    request : Request
        Объект запроса FastAPI, содержащий информацию о входящем HTTP-запросе (не используется).
    exc : FileUploadPendingException
        Экземпляр исключения, из которого получаются данные для более точного ответа.

    Returns
    -------
    JSONResponse
        Ответ с ошибкой 202.
    """
    return JSONResponse(
        content=StandardResponse(
            code=APICode.FILE_UPLOAD_PENDING,
            detail=exc.detail,
        ).model_dump(mode="json"),
        status_code=status.HTTP_202_ACCEPTED,
    )
