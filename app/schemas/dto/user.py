from datetime import datetime
from uuid import UUID

from .base import BaseDTO


class UserDTO(BaseDTO):
    """DTO для представления пользователя системы.

    Attributes
    ----------
    id : UUID
        Уникальный идентификатор пользователя.
    username : str
        Логин пользователя для входа в систему.
    password_hash : str
        Хэш пароля пользователя (никогда не передается клиенту).
    refresh_token_hash : str | None
        Хэш refresh-токена для управления сессиями.
    avatar_url : str | None
        URL аватара пользователя.
    is_active : bool
        Статус пользователя (True - активный или False - заблокирован)
    created_at : datetime
        Дата и время создания записи.
    """

    id: UUID
    username: str
    password_hash: str
    refresh_token_hash: str | None
    avatar_url: str | None
    is_active: bool
    created_at: datetime


class CreatorDTO(BaseDTO):
    """DTO для представления создателя медиа.

    Attributes
    ----------
    id : UUID
        Уникальный идентификатор пользователя.
    username : str
        Логин пользователя в системе.
    avatar_url : str | None
        URL аватара пользователя.
    is_active : bool
        Статус пользователя (True - активный или False - заблокирован)
    """

    id: UUID
    username: str
    avatar_url: str | None
    is_active: bool


class PartnerDTO(CreatorDTO):
    """DTO для представления партнёра пользователя.

    Notes
    -----
    Имеет те же поля, что и `CreatorDTO`, однако отличается
    по семантике.
    """

    pass


class CoupleDTO(BaseDTO):
    """DTO для представления пары между пользователями приложения.

    Attributes
    ----------
    partner1 : PartnerDTO
        DTO первого пользователя пары.
    partner2 : PartnerDTO
        DTO второго пользователя пары.
    """

    partner1: PartnerDTO
    partner2: PartnerDTO
