from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.core.enums import APICode
from app.core.exceptions.media import FileDeletedException
from app.main import my_love_backend
from app.schemas.v1.responses.standard import StandardResponse


@my_love_backend.exception_handler(FileDeletedException)
async def file_deleted_exception_handler(
    request: Request,
    exc: FileDeletedException,
) -> JSONResponse:
    """Обрабатывает исключения FileDeletedException.

    Возвращает клиенту ответ с HTTP 410 в случае, если запрошенный файл
    был явно удалён пользователем (статус DELETED).

    Parameters
    ----------
    request : Request
        Объект запроса FastAPI, содержащий информацию о входящем HTTP-запросе (не используется).
    exc : FileDeletedException
        Экземпляр исключения, из которого получаются данные для более точного ответа.

    Returns
    -------
    JSONResponse
        Ответ с ошибкой 410.
    """
    return JSONResponse(
        content=StandardResponse(
            code=APICode.FILE_DELETED,
            detail=exc.detail,
        ).model_dump(mode="json"),
        status_code=status.HTTP_410_GONE,
    )
