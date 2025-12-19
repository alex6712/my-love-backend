from typing import Any, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Boolean, String, Text, Uuid

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import UserModel


class AlbumModel(BaseModel):
    __tablename__ = "albums"
    __table_args__ = {"comment": "Созданные пользователями альбомы медиа"}

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        default=uuid4,
        primary_key=True,
        comment="Уникальный идентификатор альбома",
    )

    title: Mapped[str] = mapped_column(
        String(64),
        default="Новый альбом",
        nullable=False,
        comment="Наименование альбома",
    )

    description: Mapped[str] = mapped_column(
        Text(),
        nullable=True,
        comment="Описание альбома",
    )

    cover_url: Mapped[str] = mapped_column(
        String(512),
        nullable=True,
        comment="URL обложки альбома",
    )

    is_private: Mapped[bool] = mapped_column(
        Boolean(),
        default=False,
        nullable=False,
        index=True,
        comment="Видимость альбома (личный или публичный)",
    )

    created_by: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        comment="UUID пользователя, создавшего альбом",
    )

    creator: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="media_albums",
        lazy="select",
    )

    def __repr__(self, **_) -> str:
        attrs: dict[str, Any] = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "cover_url": self.cover_url,
            "is_private": self.is_private,
            "created_by": self.created_by,
        }

        return super().__repr__(**attrs)
