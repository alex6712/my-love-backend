from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, String, Text, Uuid
from sqlalchemy.types import Enum as SAEnum

from app.core.enums import FileStatus
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.album import AlbumModel
    from app.models.user import UserModel


class FileModel(BaseModel):
    __tablename__ = "files"

    object_key: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="Путь до файла внутри бакета приложения",
    )
    content_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Тип медиа файла",
    )
    status: Mapped[FileStatus] = mapped_column(
        SAEnum(
            FileStatus,
            name="file_status",
            native_enum=True,
        ),
        default=FileStatus.PENDING,
        nullable=False,
        index=True,
        comment="Текущий статус медиа-файла",
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

    __table_args__ = (
        Index(
            "ix_files_pending_created",
            "status",
            "created_at",
            postgresql_where=text("status = 'PENDING'"),
        ),
        {"comment": "Загруженные пользователями медиа файлы"},
    )

    def __repr__(self, **_) -> str:
        attrs: dict[str, Any] = {
            "object_key": self.object_key,
            "content_type": self.content_type,
            "status": self.status,
            "title": self.title,
            "description": self.description,
            "geo_data": self.geo_data,
            "created_by": self.created_by,
        }

        return super().__repr__(**attrs)
