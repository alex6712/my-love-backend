from datetime import date
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Date, Uuid

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import UserModel


class CoupleModel(BaseModel):
    __tablename__ = "couples"
    __table_args__ = (
        CheckConstraint("user_low_id < user_high_id", name="ck_couple_order"),
        UniqueConstraint("user_low_id", "user_high_id", name="uq_couple_pair"),
        {
            "comment": "Сведения о зарегистрированных парах между пользователями в приложении"
        },
    )

    user_low_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="Меньший UUID пользователя",
    )
    user_high_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="Больший UUID пользователя",
    )
    relationship_started_on: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Реальная дата начала отношений",
    )

    user_low: Mapped["UserModel"] = relationship(
        "UserModel",
        viewonly=True,
        lazy="select",
        foreign_keys=[user_low_id],
    )
    user_high: Mapped["UserModel"] = relationship(
        "UserModel",
        viewonly=True,
        lazy="select",
        foreign_keys=[user_high_id],
    )

    def __repr__(self, **_) -> str:
        attrs: dict[str, Any] = {
            "user_low_id": self.user_low_id,
            "user_high_id": self.user_high_id,
            "relationship_started_on": self.relationship_started_on,
        }

        return super().__repr__(**attrs)
