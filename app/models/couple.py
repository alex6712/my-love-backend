from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import DateTime, Uuid
from sqlalchemy.types import Enum as SAEnum

from app.core.enums import CoupleRequestStatus
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import UserModel


class CoupleRequestModel(BaseModel):
    __tablename__ = "couple_requests"
    __table_args__ = (
        CheckConstraint("initiator_id <> recipient_id", name="ck_couple_not_self"),
        {"comment": "Сведения о парах между пользователями в приложении"},
    )

    initiator_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
        comment="UUID пользователя-инициатора",
    )
    recipient_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
        comment="UUID пользователя-реципиента",
    )
    status: Mapped[CoupleRequestStatus] = mapped_column(
        SAEnum(
            CoupleRequestStatus,
            name="couple_request_status",
            native_enum=True,
        ),
        default=CoupleRequestStatus.PENDING,
        nullable=False,
        index=True,
        comment="Статус пары между пользователями",
    )
    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Дата и время принятия приглашения",
    )

    initiator: Mapped["UserModel"] = relationship(
        "UserModel",
        viewonly=True,
        lazy="select",
        foreign_keys=[initiator_id],
    )
    recipient: Mapped["UserModel"] = relationship(
        "UserModel",
        viewonly=True,
        lazy="select",
        foreign_keys=[recipient_id],
    )

    def __repr__(self, **_) -> str:
        attrs: dict[str, Any] = {
            "initiator_id": self.initiator_id,
            "recipient_id": self.recipient_id,
            "status": self.status,
            "accepted_at": self.accepted_at,
        }

        return super().__repr__(**attrs)
