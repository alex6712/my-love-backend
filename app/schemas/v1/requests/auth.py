from typing import Self

from pydantic import BaseModel, Field, model_validator

from app.core.validators import ValidatedPassword, ValidatedUsername


class RegisterRequest(BaseModel):
    """Схема запроса регистрации с валидацией.

    Attributes
    ----------
    username : str
        Логин пользователя (3-32 символа, a-z, A-Z, 0-9, _, -).
    password : str
        Пароль пользователя (минимум 12 символов, верхний/нижний регистр,
        цифра, спецсимвол).
    """

    username: ValidatedUsername = Field(
        description="Логин пользователя (3-32 символа, a-z, A-Z, 0-9, _, -)",
        examples=["john_doe", "user123"],
        json_schema_extra={
            "minLength": 3,
            "maxLength": 32,
            "pattern": "^[a-zA-Z0-9_-]+$",
        },
    )
    password: ValidatedPassword = Field(
        description="Пароль (минимум 12 символов, с цифрой, спецсимволом, верхним и нижним регистром)",
        examples=["SecureP@ss123!"],
        json_schema_extra={"minLength": 12},
    )


class ChangePasswordRequest(BaseModel):
    """Схема запроса смены пароля с валидацией совпадения паролей.

    Attributes
    ----------
    current_password : str
        Текущий пароль пользователя (минимум 12 символов, верхний/нижний
        регистр, цифра, спецсимвол).
    new_password : str
        Новый пароль пользователя (минимум 12 символов, верхний/нижний
        регистр, цифра, спецсимвол).
    confirm_password : str
        Подтверждение нового пароля. Должно совпадать с `new_password`.

    Raises
    ------
    ValueError
        Если `new_password` и `confirm_password` не совпадают.
    """

    current_password: str = Field(
        description="Текущий пароль пользователя",
        examples=["SecureP@ss111!"],
        json_schema_extra={"minLength": 12},
    )
    new_password: ValidatedPassword = Field(
        description="Новый пароль пользователя",
        examples=["SecureP@ss222!"],
        json_schema_extra={"minLength": 12},
    )
    confirm_password: str = Field(
        description="Подтверждение нового пароля пользователя",
        examples=["SecureP@ss333!"],
        json_schema_extra={"minLength": 12},
    )

    @model_validator(mode="after")
    def passwords_match(self) -> Self:
        """Проверяет совпадение нового пароля и его подтверждения."""
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")

        return self
