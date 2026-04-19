from datetime import datetime
from uuid import UUID

from app.core.types import UNSET, Maybe
from app.schemas.dto.base import BaseCreateDTO, BaseSQLCoreDTO, BaseUpdateDTO


class UserSessionDTO(BaseSQLCoreDTO):
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


class CreateUserSessionDTO(BaseCreateDTO):
    """DTO для создания новой пользовательской сессии.

    Attributes
    ----------
    id : UUID
        Идентификатор сессии.
    user_id : UUID
        UUID пользователя системы (владельца сессии).
    refresh_token_hash : str
        Хэш токена обновления сессии пользователя.
    expires_at : datetime
        Дата и время, когда токен будет просрочен.
    last_used_at : datetime | None
        Дата и время последнего обновления сессии.
    """

    id: UUID
    user_id: UUID
    refresh_token_hash: str
    expires_at: datetime
    last_used_at: datetime | None


class UpdateUserSessionDTO(BaseUpdateDTO):
    """DTO для частичного обновления пользовательской сессии.

    Attributes
    ----------
    refresh_token_hash : Maybe[str]
        Новый хэш токена обновления сессии пользователя.
        Если `UNSET` - поле не изменяется.
    expires_at : Maybe[datetime]
        Новые дата и время, когда токен будет просрочен.
        Если `UNSET` - поле не изменяется.
    last_used_at : Maybe[datetime]
        новые дата и время последнего обновления сессии.
        Если `UNSET` - поле не изменяется.
    """

    refresh_token_hash: Maybe[str] = UNSET
    expires_at: Maybe[datetime] = UNSET
    last_used_at: Maybe[datetime] = UNSET
