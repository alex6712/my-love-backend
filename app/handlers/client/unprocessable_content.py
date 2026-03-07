from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.enums import APICode
from app.core.exceptions.media import FileUploadFailedException
from app.main import my_love_backend
from app.schemas.v1.responses.standard import StandardResponse
from app.schemas.v1.responses.validation_error import ValidationErrorResponse


@my_love_backend.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Обрабатывает ошибки валидации данных RequestValidationError.

    Возвращает клиенту стандартизированный ответ с ошибкой 422
    и подробным списком ошибок валидации.

    Parameters
    ----------
    request : Request
        Объект запроса с информацией о входящем HTTP-запросе.
    exc : RateLimitExceeded
        Исключение, вызвавшее ошибку 422.

    Returns
    -------
    JSONResponse
        Ответ с ошибкой 422, кодом VALIDATION_ERROR.
    """
    return JSONResponse(
        content=ValidationErrorResponse(
            code=APICode.VALIDATION_ERROR,
            detail=jsonable_encoder(exc.errors()),
        ).model_dump(mode="json"),
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )


@my_love_backend.exception_handler(FileUploadFailedException)
async def file_upload_failed_exception_handler(
    request: Request,
    exc: FileUploadFailedException,
) -> JSONResponse:
    """Обрабатывает исключения FileUploadFailedException.

    Возвращает клиенту ответ с HTTP 422 в случае, если загрузка
    запрошенного файла завершилась ошибкой (статус FAILED).

    Parameters
    ----------
    request : Request
        Объект запроса FastAPI, содержащий информацию о входящем HTTP-запросе (не используется).
    exc : FileUploadFailedException
        Экземпляр исключения, из которого получаются данные для более точного ответа.

    Returns
    -------
    JSONResponse
        Ответ с ошибкой 422.
    """
    return JSONResponse(
        content=StandardResponse(
            code=APICode.FILE_UPLOAD_FAILED,
            detail=exc.detail,
        ).model_dump(mode="json"),
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )
