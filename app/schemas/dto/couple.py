from datetime import date, datetime
from uuid import UUID

from app.core.enums import CoupleRequestStatus
from app.core.types import UNSET, Maybe
from app.schemas.dto.base import BaseCreateDTO, BaseSQLCoreDTO, BaseUpdateDTO
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


class CreateCoupleDTO(BaseCreateDTO):
    user_low_id: UUID
    user_high_id: UUID
    relationship_started_on: date | None = None


class UpdateCoupleDTO(BaseUpdateDTO):
    """DTO для частичного обновления данных о паре.

    Attributes
    ----------
    relationship_started_on : Maybe[date | None]
        Новая реальная дата начала отношений (или None для сброса значения).
        Если `UNSET` - поле не изменяется.
    """

    relationship_started_on: Maybe[date | None] = UNSET
