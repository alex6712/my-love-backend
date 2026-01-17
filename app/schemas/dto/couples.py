from datetime import datetime

from app.core.enums import CoupleRequestStatus
from app.schemas.dto.base import BaseSQLModelDTO
from app.schemas.dto.users import PartnerDTO


class CoupleRequestDTO(BaseSQLModelDTO):
    """DTO для представления пары между пользователями приложения.

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
