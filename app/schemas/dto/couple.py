from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from app.core.enums import CoupleRequestStatus
from app.core.types import UNIQUE, UNSET, Maybe
from app.schemas.dto.base import (
    BaseCreateDTO,
    BaseFilterManyDTO,
    BaseFilterOneDTO,
    BaseSQLCoreDTO,
    BaseUpdateDTO,
)
from app.schemas.dto.user import PartnerDTO


class CoupleRequestDTO(BaseSQLCoreDTO):
    """DTO для представления запроса на создание пары между
    пользователями приложения.

    Attributes
    ----------
    initiator : PartnerDTO
        DTO пользователя-инициатора.
    recipient : PartnerDTO
        DTO пользователя-реципиента.
    status : CoupleStatus
        Текущий статус пары.
    accepted_at : datetime | None
        Дата и время принятия приглашения в пару.
    """

    initiator: PartnerDTO
    recipient: PartnerDTO
    status: CoupleRequestStatus
    accepted_at: datetime | None


class CoupleDTO(BaseSQLCoreDTO):
    """DTO для представления пары между пользователями приложения.

    Attributes
    ----------
    first_user : PartnerDTO
        DTO первого пользователя члена пары.
    second_user : PartnerDTO
        DTO второго пользователя члена пары.
    relationship_started_on : date | None
        Реальная дата начала отношений.
    """

    first_user: PartnerDTO
    second_user: PartnerDTO
    relationship_started_on: date | None


class FilterOneCoupleRequestDTO(BaseFilterOneDTO):
    """DTO для фильтрации заявок на пару.

    Attributes
    ----------
    id : Maybe[UUID]
        Идентификатор запроса. Является уникальным полем - достаточно передать
        только его для однозначного нахождения записи.
    initiator_id : Maybe[UUID]
        Идентификатор инициатора запроса.
    recipient_id : Maybe[UUID]
        Идентификатор получателя запроса.
    status : Maybe[CoupleRequestStatus]
        Статус запроса.
    """

    id: Annotated[Maybe[UUID], UNIQUE] = UNSET

    initiator_id: Maybe[UUID] = UNSET
    recipient_id: Maybe[UUID] = UNSET
    status: Maybe[CoupleRequestStatus] = UNSET


class FilterOneCoupleDTO(BaseFilterOneDTO):
    """DTO для поиска одной записи пары по идентификатору пары или пользователя.

    Требует передачи хотя бы одного из уникальных полей: `couple_id` или
    `user_id`. Используется в сервисах, где пару можно найти как по её
    собственному идентификатору, так и по идентификатору одного из участников.

    Attributes
    ----------
    couple_id : Maybe[UUID]
        Идентификатор пары. Является уникальным полем - достаточно передать
        только его для однозначного нахождения записи.
    user_id : Maybe[UUID]
        Идентификатор пользователя, входящего в пару. Является уникальным
        полем - достаточно передать только его для однозначного нахождения записи.
    """

    couple_id: Annotated[Maybe[UUID], UNIQUE] = UNSET
    user_id: Annotated[Maybe[UUID], UNIQUE] = UNSET


class FilterManyCoupleRequestsDTO(BaseFilterManyDTO):
    ids: Maybe[list[UUID]] = UNSET
    initiator_ids: Maybe[list[UUID]] = UNSET
    recipient_ids: Maybe[list[UUID]] = UNSET
    statuses: Maybe[list[CoupleRequestStatus]] = UNSET


class CreateCoupleRequestDTO(BaseCreateDTO):
    """DTO для создания запроса на пару.

    Attributes
    ----------
    initiator_id : UUID
        Идентификатор пользователя, отправившего заявку.
    recipient_id : UUID
        Идентификатор пользователя, которому адресована заявка.
    status : CoupleRequestStatus
        Начальный статус запроса.
    accepted_at : datetime | None
        Дата и время принятия запроса. None, если заявка ещё не принята.
    """

    initiator_id: UUID
    recipient_id: UUID
    status: CoupleRequestStatus
    accepted_at: datetime | None


class CreateCoupleDTO(BaseCreateDTO):
    """DTO для создания пары.

    Идентификаторы пользователей хранятся в лексикографическом порядке:
    `user_low_id` всегда меньше `user_high_id`. Это обеспечивает
    уникальность пары независимо от порядка передачи участников.

    Attributes
    ----------
    first_user_id : UUID
        Идентификатор первого пользователя члена пары.
    second_user_id : UUID
        Идентификатор второго пользователя члена пары.
    relationship_started_on : date | None
        Дата начала отношений, указанная пользователями. None, если не задана.
    """

    first_user_id: UUID
    second_user_id: UUID
    relationship_started_on: date | None


class UpdateCoupleRequestDTO(BaseUpdateDTO):
    """DTO для обновления запроса на пару.

    Attributes
    ----------
    status : Maybe[CoupleRequestStatus]
        Новый статус запроса.
    accepted_at : Maybe[datetime | None]
        Новая дата и время принятия запроса. Может быть явно передан как None
        для сброса значения.
    """

    status: Maybe[CoupleRequestStatus] = UNSET
    accepted_at: Maybe[datetime | None] = UNSET


class UpdateCoupleDTO(BaseUpdateDTO):
    """DTO для частичного обновления данных о паре.

    Attributes
    ----------
    relationship_started_on : Maybe[date | None]
        Новая реальная дата начала отношений (или None для сброса значения).
        Если `UNSET` - поле не изменяется.
    """

    relationship_started_on: Maybe[date | None] = UNSET
