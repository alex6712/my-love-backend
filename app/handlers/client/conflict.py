from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.core.enums import APICode
from app.core.exceptions.base import AlreadyExistsException, IdempotencyException
from app.main import my_love_backend
from app.schemas.v1.responses.standard import StandardResponse


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


@my_love_backend.exception_handler(IdempotencyException)
async def idempotency_exception_handler(
    request: Request,
    exc: IdempotencyException,
) -> JSONResponse:
    """Обрабатывает исключения IdempotencyException.

    Специализированный обработчик для случаев, когда по переданному ключу
    идемпотентности обработка запроса уже начата.

    Parameters
    ----------
    request : Request
        Объект входящего HTTP-запроса (не используется).
    exc : IdempotencyException
        Экземпляр исключения для предоставления более детального сообщения об ошибке.

    Returns
    -------
    JSONResponse
        Ответ с указанием на то, что запрос уже в обработке.
    """
    return JSONResponse(
        content=StandardResponse(
            code=APICode.IDEMPOTENCY_CONFLICT,
            detail=exc.detail,
        ).model_dump(mode="json"),
        status_code=status.HTTP_409_CONFLICT,
    )
