from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.core.enums import APICode
from app.core.exceptions.media import FilePresignedUrlGenerationFailedException
from app.main import my_love_backend
from app.schemas.v1.responses.standard import StandardResponse


@my_love_backend.exception_handler(FilePresignedUrlGenerationFailedException)
async def file_presigned_url_generation_failed_exception_handler(
    request: Request,
    exc: FilePresignedUrlGenerationFailedException,
) -> JSONResponse:
    """Обрабатывает исключения FilePresignedUrlGenerationFailedException.

    Возвращает клиенту ответ с HTTP 503 в случае, если S3-клиент не смог
    сгенерировать presigned URL для доступа к файлу.

    Parameters
    ----------
    request : Request
        Объект запроса FastAPI, содержащий информацию о входящем HTTP-запросе (не используется).
    exc : FilePresignedUrlGenerationFailedException
        Экземпляр исключения, из которого получаются данные для более точного ответа.

    Returns
    -------
    JSONResponse
        Ответ с ошибкой 503.
    """
    return JSONResponse(
        content=StandardResponse(
            code=APICode.FILE_PRESIGNED_URL_GENERATION_FAILED,
            detail=exc.detail,
        ).model_dump(mode="json"),
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    )
