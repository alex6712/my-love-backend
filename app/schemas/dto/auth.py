from uuid import UUID

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


class LoginResult(BaseModel):
    """Результат успешной аутентификации пользователя.

    Объединяет JWT-токены и минимальный набор публичных
    данных пользователя, возвращаемых endpoint'ом `/auth/login`
    в качестве тела ответа (после установки auth-cookie).

    Attributes
    ----------
    user_id : UUID
        Идентификатор аутентифицированного пользователя.
    username : str
        Логин аутентифицированного пользователя.
    tokens : Tokens
        Пара выпущенных JWT-токенов, которая будет
        установлена клиенту в виде HttpOnly-cookie.
    """

    user_id: UUID
    username: str
    tokens: Tokens
