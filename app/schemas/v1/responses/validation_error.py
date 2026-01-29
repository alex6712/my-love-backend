from pydantic import Field
from pydantic_core import ErrorDetails

from app.core.enums import APICode
from app.schemas.v1.responses.standard import BaseResponse


class ValidationErrorResponse(BaseResponse):
    """Переопределённая модель HTTPValidationError.

    Является переопределением модели HTTPValidationError из FastAPI.
    Это сделано для добавления в эту модель атрибута `code`, чтобы
    сохранить консистентность ответов API.

    Attributes
    ----------
    code : int
        HTTP-код ответа сервера.
    detail : list[ErrorDetails]
        Список ошибок валидации.
    """

    code: APICode = Field(
        default=APICode.VALIDATION_ERROR,
        description="Статус ответа от сервера в виде API Enum",
        examples=[APICode.VALIDATION_ERROR],
    )
    detail: list[ErrorDetails] = Field(
        description="Список ошибок валидации переданных данных.",
    )
