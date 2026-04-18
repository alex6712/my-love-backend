from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import SmallInteger, Uuid

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.couple import CoupleModel
    from app.models.user import UserModel


class CoupleMemberModel(BaseModel):
    __tablename__ = "couple_members"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_one_couple_per_user"),
        UniqueConstraint("couple_id", "slot", name="uq_couple_slot"),
        CheckConstraint("slot IN (1, 2)", name="ck_slot_values"),
        {"comment": "Таблица с записями о состоящих в парах пользователях"},
    )

    couple_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("couples.id", ondelete="CASCADE"),
        nullable=False,
        comment="UUID пары",
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="UUID пользователя",
    )
    slot: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        comment="Слот пользователя: 1 или 2",
    )

    couple: Mapped["CoupleModel"] = relationship(
        "CoupleModel",
        viewonly=True,
        lazy="raise",
        foreign_keys=[couple_id],
    )
    user: Mapped["UserModel"] = relationship(
        "UserModel",
        viewonly=True,
        lazy="raise",
        foreign_keys=[user_id],
    )

    def __repr__(self, **_) -> str:
        attrs: dict[str, Any] = {
            "couple_id": self.couple_id,
            "user_id": self.user_id,
            "slot": self.slot,
        }

        return super().__repr__(**attrs)
