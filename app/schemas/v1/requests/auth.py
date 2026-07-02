from typing import Self

from pydantic import BaseModel, Field, model_validator

from app.core.consts import (
    DISPLAY_NAME_MAX_LENGTH,
    DISPLAY_NAME_MIN_LENGTH,
    PASSWORD_MIN_LENGTH,
    USERNAME_MAX_LENGTH,
    USERNAME_MIN_LENGTH,
)
from app.core.validation import (
    ValidatedDisplayName,
    ValidatedPassword,
    ValidatedUsername,
)


class RegisterRequest(BaseModel):
    """Схема запроса регистрации с валидацией.

    Attributes
    ----------
    username : str
        Логин пользователя.
    password : str
        Пароль пользователя.
    display_name : str
        Отображаемое имя пользователя.
    """

    username: ValidatedUsername = Field(
        description=f"Логин пользователя ({USERNAME_MIN_LENGTH}-{USERNAME_MAX_LENGTH} символа, a-z, A-Z, 0-9, _, -)",
        examples=["john_doe", "user123"],
    )
    password: ValidatedPassword = Field(
        description=f"Пароль (минимум {PASSWORD_MIN_LENGTH} символов, с цифрой, спецсимволом, верхним и нижним регистром)",
        examples=["SecureP@ss123!"],
        json_schema_extra={"sensitive": True},
    )
    display_name: ValidatedDisplayName = Field(
        description=f"Отображаемое имя пользователя ({DISPLAY_NAME_MIN_LENGTH}-{DISPLAY_NAME_MAX_LENGTH} символа, любые Unicode-символы)",
        examples=["Александр", "7", "一只非常重要的鸡", "🍆"],
    )


class ChangePasswordRequest(BaseModel):
    """Схема запроса смены пароля с валидацией совпадения паролей.

    Attributes
    ----------
    current_password : str
        Текущий пароль пользователя.
    new_password : str
        Новый пароль пользователя.
    confirm_password : str
        Подтверждение нового пароля. Должно совпадать с `new_password`.

    Raises
    ------
    ValueError
        Если `new_password` и `confirm_password` не совпадают.

    Notes
    -----
    Атрибут `current_password` не проверяется валидатором.
    Правила сложности паролей могут меняться со временем.
    Если проверять старый пароль по новым правилам, смена пароля
    может стать невозможной для пользователя.
    """

    current_password: str = Field(
        description="Текущий пароль пользователя",
        examples=["SecureP@ss111!"],
        json_schema_extra={"sensitive": True},
    )
    new_password: ValidatedPassword = Field(
        description="Новый пароль пользователя",
        examples=["SecureP@ss222!"],
        json_schema_extra={"sensitive": True},
    )
    confirm_password: str = Field(
        description="Подтверждение нового пароля пользователя",
        examples=["SecureP@ss333!"],
        json_schema_extra={"sensitive": True},
    )

    @model_validator(mode="after")
    def passwords_match(self) -> Self:
        """Проверяет совпадение нового пароля и его подтверждения.

        Raises
        ------
        ValueError
            Если значения `new_password` и `confirm_password` отличаются.
            Сообщение об ошибке формулируется так, чтобы быть понятным в логах
            и при ответе API.
        """
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")

        return self
