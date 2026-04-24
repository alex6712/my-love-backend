from datetime import date

from pydantic import BaseModel, Field

from app.core.types import UNSET, Maybe


class CreateCoupleRequest(BaseModel):
    """Схема запроса на создание пары между пользователями.

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


class PatchCoupleRequest(BaseModel):
    """Схема запроса на частичное редактирование деталей пары.

    Используется в качестве представления данных для частичного
    обновления полей пары между пользователями. Все поля опциональны -
    передаются только те атрибуты, которые необходимо изменить.

    Attributes
    ----------
    relationship_started_on : Maybe[date | None]
        Новая реальная дата начала отношений. Если не передан - остаётся `UNSET`
        и текущее значение в базе данных не изменяется.
    """

    relationship_started_on: Maybe[date | None] = Field(
        default_factory=lambda: UNSET,
        description="Новая реальная дата начала отношений",
        examples=["2026-04-24"],
    )
