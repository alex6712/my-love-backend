from datetime import datetime
from uuid import UUID

from app.schemas.dto.base import BaseSQLModelDTO


class UserSessionDTO(BaseSQLModelDTO):
    """DTO для представления сессии пользователя системы.

    Attributes
    ----------
    user_id : UUID
        UUID пользователя системы (владельца сессии).
    refresh_token_hash : str
        Хеш токена обновления сессии пользователя.
    expires_at : datetime
        Дата и время, когда токен будет просрочен.
    last_used_at : datetime
        Дата и время последнего обновления сессии.
    is_active : bool
        Статус сессии (True - активна или False - отозвана).
    """

    user_id: UUID
    refresh_token_hash: str
    expires_at: datetime
    last_used_at: datetime
    is_active: bool
