from pydantic import field_validator

from app.core.enums import IdempotencyStatus
from app.schemas.dto.base import BaseDTO


class IdempotencyKeyDTO(BaseDTO):
    """DTO для представления ключа идемпотентности.

    Attributes
    ----------
    status : IdempotencyStatus
        Текущий статус запроса.
    response : str | None
        Ответ от сервера.
    """

    status: IdempotencyStatus
    response: str | None

    @field_validator("response", mode="after")
    @classmethod
    def validate_response(cls, value: str) -> str | None:
        """Превращает пустую строку ответа в None."""
        return None if value == "" else value
