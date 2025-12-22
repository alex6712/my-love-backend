from uuid import UUID

from pydantic import BaseModel, Field


class CreateCoupleRequest(BaseModel):
    """Схема запроса на создание пары между пользователями..

    Attributes
    ----------
    partner_id : UUID
        UUID пользователя-партнёра.
    """

    partner_id: UUID = Field(
        description="UUID пользователя-партнёра.",
        examples=["db78891b-8555-4c7f-91b9-84516c61c394"],
    )
