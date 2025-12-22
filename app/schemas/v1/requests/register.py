from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    """Схема объекта пользователя с паролем.

    Используется в качестве представления информации о пользователе, включая его пароль.

    Attributes
    ----------
    username : str
        Логин пользователя.
    password : str
        Пароль пользователя.
    """

    username: str = Field(description="Логин пользователя", examples=["someone"])
    password: str = Field(
        description="Пароль пользователя в открытом формате", examples=["password"]
    )
