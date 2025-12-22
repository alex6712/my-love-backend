from pydantic import Field

from app.schemas.dto.user import PartnerDTO
from app.schemas.v1.responses.standard import StandardResponse


class PartnerResponse(StandardResponse):
    """Модель ответа сервера с информацией о партнёре пользователя.

    Attributes
    ----------
    partner : PartnerDTO | None
        DTO партнёра пользователя, или None если партнёр не найден.
    """

    partner: PartnerDTO | None = Field(
        description="DTO партнёра пользователя, или None если партнёр не найден.",
    )
