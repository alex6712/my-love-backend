from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import UserModel


class CoupleModel(BaseModel):
    __tablename__ = "couples"
    __table_args__ = (
        CheckConstraint("partner1_id <> partner2_id", name="ck_couple_not_self"),
        {"comment": "Сведения о парах, зарегистрированных в приложении"},
    )

    partner1_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        comment="UUID первого пользователя пары",
    )
    partner2_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        comment="UUID второго пользователя пары",
    )

    partner1: Mapped["UserModel"] = relationship(
        "UserModel",
        foreign_keys=[partner1_id],
        lazy="selectin",
    )
    partner2: Mapped["UserModel"] = relationship(
        "UserModel",
        foreign_keys=[partner2_id],
        lazy="selectin",
    )

    def __repr__(self, **_) -> str:
        attrs: dict[str, Any] = {
            "partner1_id": self.partner1_id,
            "partner2_id": self.partner2_id,
        }

        return super().__repr__(**attrs)
