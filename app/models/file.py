from typing import TYPE_CHECKING, Any, Literal
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, String, Text, Uuid

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.album import AlbumModel
    from app.models.user import UserModel

type FileType = Literal["image", "video"]


class FileModel(BaseModel):
    __tablename__ = "files"
    __table_args__ = {"comment": "Загруженные пользователями медиа файлы"}

    object_key: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="Путь до файла внутри бакета приложения",
    )
    type_: Mapped[FileType] = mapped_column(
        String(16),
        nullable=False,
        comment="Тип медиа файла",
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
    geo_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON(),
        default=None,
        nullable=True,
        comment="Данные о местоположении сохранённого медиа",
    )
    created_by: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="UUID пользователя, загрузившего медиа",
    )

    creator: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="media_files",
        viewonly=True,
        lazy="select",
    )
    album: Mapped["AlbumModel"] = relationship(
        "AlbumModel",
        secondary="album_items",
        cascade="all, delete-orphan",
        viewonly=True,
        lazy="select",
    )

    def __repr__(self, **_) -> str:
        attrs: dict[str, Any] = {
            "object_key": self.object_key,
            "type_": self.type_,
            "title": self.title,
            "description": self.description,
            "geo_data": self.geo_data,
            "created_by": self.created_by,
        }

        return super().__repr__(**attrs)
