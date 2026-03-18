from pydantic import BaseModel


class Tokens(BaseModel):
    """DTO для передачи пары JWT-токенов.

    Используется в ответах API при аутентификации и обновлении сессии.
    Содержит access-токен для авторизации запросов и refresh-токен
    для получения новой пары токенов.

    Attributes
    ----------
    access : str
        JWT access-токен с коротким временем жизни, используется
        для авторизации запросов к API.
    refresh : str
        JWT refresh-токен с более длительным временем жизни,
        используется для обновления access-токена.
    """

    access: str
    refresh: str
