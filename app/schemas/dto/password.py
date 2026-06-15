from typing import Union

from pydantic import BaseModel, Field

from app.core.enums import PasswordRuleType


class PasswordRule(BaseModel):
    """Модель отдельного правила валидации пароля.

    Атрибуты
    --------
    id : str
        Машиночитаемый идентификатор (например, ``"min_length"``).
    description : str
        Человекочитаемое описание на английском языке.
    type : PasswordRuleType
        Тип значения поля `value`: ``min``, ``max``, ``boolean``, ``charset``.
    value : int | bool | str
        Значение правила.
    unit : str | None
        Единица измерения (например, ``"characters"``) или ``None``.
    """

    id: str = Field(
        description="Машиночитаемый идентификатор правила",
        examples=["min_length"],
    )
    description: str = Field(
        description="Человекочитаемое описание на английском языке",
        examples=["Minimum password length"],
    )
    type: PasswordRuleType = Field(description="Тип значения поля `value`")
    value: Union[bool, int, str] = Field(
        description="Значение правила в соответствии с его типом"
    )
    unit: str | None = Field(
        default=None,
        description="Единица измерения (например, 'characters') или null",
        examples=["characters"],
    )
