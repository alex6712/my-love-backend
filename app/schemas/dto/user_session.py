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
        Хэш токена обновления сессии пользователя.
    expires_at : datetime
        Дата и время, когда токен будет просрочен.
    last_used_at : datetime
        Дата и время последнего обновления сессии.
    """

    user_id: UUID
    refresh_token_hash: str
    expires_at: datetime
    last_used_at: datetime
