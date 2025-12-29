from datetime import datetime
from uuid import UUID

from app.core.enums import CoupleRequestStatus
from app.schemas.dto.base import BaseDTO
from app.schemas.dto.users import PartnerDTO


class CoupleRequestDTO(BaseDTO):
    """DTO для представления пары между пользователями приложения.

    Attributes
    ----------
    id : UUID
        UUID запроса на создание пары.
    initiator : PartnerDTO
        DTO пользователя-инициатора.
    recipient : PartnerDTO
        DTO пользователя-реципиента.
    status : CoupleStatus
        Текущий статус пары.
    accepted_at : datetime | None
        Дата и время принятия приглашения в пару.
    """

    id: UUID
    initiator: PartnerDTO
    recipient: PartnerDTO
    status: CoupleRequestStatus
    accepted_at: datetime | None
