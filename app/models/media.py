from typing import TYPE_CHECKING, Any, Literal
from uuid import UUID

from pydantic import FileUrl
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, String, Text, Uuid

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.album import AlbumModel
    from app.models.user import UserModel

type MediaType = Literal["image", "video"]


class MediaModel(BaseModel):
    __tablename__ = "media"
    __table_args__ = {"comment": "Загруженные пользователями медиа файлы"}

    url: Mapped[FileUrl] = mapped_column(
        String(512),
        nullable=False,
        comment="Ссылка на файл в S3 хранилище",
    )
    type_: Mapped[MediaType] = mapped_column(
        String(16),
        nullable=False,
        comment="Тип медиа контента",
    )
    title: Mapped[str] = mapped_column(
        String(64),
        default="Новый файл",
        nullable=False,
        comment="Наименование медиа файла",
    )
    description: Mapped[str | None] = mapped_column(
        Text(),
        nullable=True,
        comment="Описание медиа файла",
    )
    geo_data: Mapped[dict[str, Any]] = mapped_column(
        JSON(),
        default=None,
        nullable=True,
        comment="Данные о местоположении сохранённого медиа",
    )
    created_by: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        comment="UUID пользователя, загрузившего медиа",
    )
    album_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("albums.id"),
        nullable=True,
        comment="UUID альбома, в который добавлено медиа",
    )

    creator: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="media_items",
        viewonly=True,
        lazy="select",
    )
    album: Mapped["AlbumModel"] = relationship(
        "AlbumModel",
        back_populates="items",
        viewonly=True,
        lazy="select",
    )

    def __repr__(self, **_) -> str:
        attrs: dict[str, Any] = {
            "url": self.url,
            "type_": self.type_,
            "title": self.title,
            "description": self.description,
            "geo_data": self.geo_data,
            "created_by": self.created_by,
            "album_id": self.album_id,
        }

        return super().__repr__(**attrs)
