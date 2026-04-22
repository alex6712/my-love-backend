from datetime import date, datetime
from uuid import UUID

from app.core.enums import CoupleRequestStatus
from app.core.types import UNSET, Maybe
from app.schemas.dto.base import (
    BaseCreateDTO,
    BaseFilterDTO,
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
    user_low : PartnerDTO
        DTO пользователя с меньшим UUID в паре.
    user_high : PartnerDTO
        DTO пользователя с большим UUID в паре.
    relationship_started_on : date | None
        Реальная дата начала отношений.
    """

    user_low: PartnerDTO
    user_high: PartnerDTO
    relationship_started_on: date | None


class FilterCoupleRequestDTO(BaseFilterDTO):
    """DTO для фильтрации заявок на пару.

    Attributes
    ----------
    id : Maybe[UUID]
        Идентификатор запроса.
    initiator_id : Maybe[UUID]
        Идентификатор инициатора запроса.
    recipient_id : Maybe[UUID]
        Идентификатор получателя запроса.
    status : Maybe[CoupleRequestStatus]
        Статус запроса.
    """

    id: Maybe[UUID] = UNSET
    initiator_id: Maybe[UUID] = UNSET
    recipient_id: Maybe[UUID] = UNSET
    status: Maybe[CoupleRequestStatus] = UNSET


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
    user_low_id : UUID
        Идентификатор пользователя с меньшим UUID.
    user_high_id : UUID
        Идентификатор пользователя с большим UUID.
    relationship_started_on : date | None
        Дата начала отношений, указанная пользователями. None, если не задана.
    """

    user_low_id: UUID
    user_high_id: UUID
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
