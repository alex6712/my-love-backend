from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Boolean, String, Text, Uuid

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.media import MediaModel
    from app.models.user import UserModel


class AlbumModel(BaseModel):
    __tablename__ = "albums"
    __table_args__ = {"comment": "Созданные пользователями альбомы медиа"}

    title: Mapped[str] = mapped_column(
        String(64),
        default="Новый альбом",
        nullable=False,
        comment="Наименование альбома",
    )
    description: Mapped[str | None] = mapped_column(
        Text(),
        nullable=True,
        comment="Описание альбома",
    )
    cover_url: Mapped[str | None] = mapped_column(
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
        viewonly=True,
        lazy="select",
    )
    items: Mapped[list["MediaModel"]] = relationship(
        "MediaModel",
        secondary="album_items",
        cascade="all, delete-orphan",
        viewonly=True,
        lazy="select",
    )

    def __repr__(self, **_) -> str:
        attrs: dict[str, Any] = {
            "title": self.title,
            "description": self.description,
            "cover_url": self.cover_url,
            "is_private": self.is_private,
            "created_by": self.created_by,
        }

        return super().__repr__(**attrs)
