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

    username: str = Field(examples=["someone"])
    password: str = Field(examples=["password"])
