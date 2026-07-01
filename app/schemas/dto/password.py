from typing import Callable

from pydantic import BaseModel, Field

from app.core.enums import PasswordRuleType


class PasswordRule(BaseModel):
    """Модель отдельного правила валидации пароля.

    Attributes
    ----------
    id : str
        Машиночитаемый идентификатор (например, `"min_length"`).
    description : str
        Человекочитаемое описание на английском языке.
    type : PasswordRuleType
        Тип значения поля `value`: `min`, `max`, `boolean`, `charset`.
    value : int | bool | str
        Значение правила.
    unit : str | None
        Единица измерения (например, `"characters"`) или `None`.
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
    value: bool | int | str = Field(
        description="Значение правила в соответствии с его типом"
    )
    unit: str | None = Field(
        default=None,
        description="Единица измерения (например, 'characters') или null",
        examples=["characters"],
    )


class PasswordRuleSpec(PasswordRule):
    """Модель отдельного правила валидации пароля с callable валидации.

    Attributes
    ----------
    check : Callable[[str], bool] | None
        Предикат для проверки пароля. `None` - правило информационное
        и не участвует в валидации (например, допустимый набор
        спецсимволов - он лишь описывает `SPECIAL_CHAR_PATTERN`,
        а сама проверка на его наличие вынесена в отдельное правило).
    """

    check: Callable[[str], bool] | None = None
