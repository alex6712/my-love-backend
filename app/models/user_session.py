from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import DateTime, String, Uuid

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import UserModel


class UserSessionModel(BaseModel):
    __tablename__ = "user_sessions"
    __table_args__ = {"comment": "Информация о пользовательских сессиях"}

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="Уникальный идентификатор пользователя",
    )
    refresh_token_hash: Mapped[str | None] = mapped_column(
        String(128),
        nullable=False,
        index=True,
        comment="Хеш токена обновления (Argon2id)",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Дата и время, когда токен будет просрочен",
    )
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Дата и время последнего обновления сессии",
    )

    user: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="sessions",
        viewonly=True,
        lazy="select",
    )

    def __repr__(self, **_) -> str:
        attrs: dict[str, Any] = {
            "user_id": self.user_id,
            "expires_at": self.expires_at,
            "last_used_at": self.last_used_at,
        }

        return super().__repr__(**attrs)
