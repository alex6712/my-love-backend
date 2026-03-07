from fastapi import Request, status
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.core.enums import APICode
from app.main import my_love_backend
from app.schemas.v1.responses.standard import StandardResponse


@my_love_backend.exception_handler(RateLimitExceeded)
async def rate_limit_exception_handler(
    request: Request,
    exc: RateLimitExceeded,
) -> JSONResponse:
    """Обрабатывает ошибки rate limiting (429 Too Many Requests).

    Возвращает клиенту стандартизированный ответ с ошибкой 429
    и рекомендуемым заголовком Retry-After.

    Parameters
    ----------
    request : Request
        Объект запроса с информацией о входящем HTTP-запросе.
    exc : RateLimitExceeded
        Исключение, вызвавшее ошибку 429 (не используется).

    Returns
    -------
    JSONResponse
        Ответ с ошибкой 429, кодом RATE_LIMIT_EXCEEDED.
    """
    response = JSONResponse(
        content=StandardResponse(
            code=APICode.RATE_LIMIT_EXCEEDED,
            detail="Too many requests. Please slow down.",
        ).model_dump(mode="json"),
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
    )

    request.app.state.limiter._inject_headers(response, request.state.view_rate_limit)

    return response
