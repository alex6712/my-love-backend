from datetime import datetime
from typing import Annotated
from uuid import UUID

from app.core.filtering import ColumnAlias
from app.core.types import UNIQUE, UNSET, Maybe
from app.schemas.dto.base import (
    BaseCreateDTO,
    BaseFilterManyDTO,
    BaseFilterOneDTO,
    BaseSQLCoreDTO,
    BaseUpdateDTO,
)


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


class FilterOneUserSessionDTO(BaseFilterOneDTO):
    """DTO для поиска одной записи сессии пользователя.

    Требует передачи хотя бы одного из уникальных полей: `id` или `refresh_token_hash`.
    Используется в сервисах, где сессию можно найти по её идентификатору или по уникальному
    хэшу рефреш-токена.

    Attributes
    ----------
    id : Maybe[UUID]
        Идентификатор сессии. Является уникальным полем - достаточно передать только его
        для однозначного нахождения записи.
    refresh_token_hash : Maybe[str]
        Хэш рефреш-токена. Является уникальным полем - достаточно передать только его
        для однозначного нахождения записи.
    user_id : Maybe[UUID]
        Идентификатор пользователя, к которому относится сессия. Не является уникальным
        для поиска одной записи, но может использоваться для дополнительной фильтрации.
    """

    id: Annotated[Maybe[UUID], UNIQUE] = UNSET
    refresh_token_hash: Annotated[Maybe[str], UNIQUE] = UNSET

    user_id: Maybe[UUID] = UNSET


class FilterManyUserSessionsDTO(BaseFilterManyDTO):
    """DTO для фильтрации множества сессий пользователей.

    Все поля опциональны — пустой DTO возвращает все записи.
    При передаче нескольких полей условия комбинируются через AND.

    Attributes
    ----------
    ids : Maybe[list[UUID]]
        Список идентификаторов сессий.
    user_ids : Maybe[list[UUID]]
        Список идентификаторов пользователей.
    refresh_token_hashes : Maybe[list[str]]
        Список хэшей рефреш-токенов.
    """

    ids: Annotated[Maybe[list[UUID]], ColumnAlias("id")] = UNSET
    user_ids: Annotated[Maybe[list[UUID]], ColumnAlias("user_id")] = UNSET
    refresh_token_hashes: Annotated[
        Maybe[list[str]], ColumnAlias("refresh_token_hash")
    ] = UNSET


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
