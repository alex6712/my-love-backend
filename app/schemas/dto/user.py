from uuid import UUID

from .base import BaseDTO


class UserDTO(BaseDTO):
    """DTO для представления пользователя системы.

    Attributes
    ----------
    id : UUID
        Уникальный идентификатор пользователя
    username : str
        Логин пользователя для входа в систему
    password_hash : str
        Хэш пароля пользователя (никогда не передается клиенту)
    refresh_token_hash : str | None
        Хэш refresh-токена для управления сессиями
    """

    id: UUID
    username: str
    password_hash: str
    refresh_token_hash: str | None
