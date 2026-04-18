from datetime import date
from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Date

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import UserModel


class CoupleModel(BaseModel):
    __tablename__ = "couples"
    __table_args__ = {
        "comment": "Сведения о зарегистрированных парах между пользователями в приложении"
    }

    relationship_started_on: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Реальная дата начала отношений",
    )

    members: Mapped[list["UserModel"]] = relationship(
        "UserModel",
        secondary="couple_members",
        viewonly=True,
        lazy="raise",
    )

    def __repr__(self, **_) -> str:
        attrs: dict[str, Any] = {
            "relationship_started_on": self.relationship_started_on,
        }

        return super().__repr__(**attrs)
