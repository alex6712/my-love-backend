from pydantic import BaseModel, Field


class CreateCoupleRequest(BaseModel):
    """Схема запроса на создание пары между пользователями..

    Attributes
    ----------
    partner_username : str
        Username пользователя-партнёра.
    """

    partner_username: str = Field(
        description="Username пользователя-партнёра.",
        examples=["partner_username"],
        min_length=1,
        max_length=64,
    )
