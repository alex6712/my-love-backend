from pydantic import BaseModel, Field

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
