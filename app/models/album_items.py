from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.types import Uuid

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.album import AlbumModel
    from app.models.file import FileModel


class AlbumItemsModel(BaseModel):
    __tablename__ = "album_items"
    __table_args__ = (
        UniqueConstraint("album_id", "file_id", name="uq_album_file"),
        {"comment": "Таблица с записями о сохранённых в альбомах медиа."},
    )

    album_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("albums.id", ondelete="CASCADE"),
        nullable=False,
        comment="UUID медиа альбома",
    )
    file_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        comment="UUID медиа файла",
    )

    album: Mapped["AlbumModel"] = relationship(
        "AlbumModel",
        viewonly=True,
        lazy="select",
        foreign_keys=[album_id],
    )
    file: Mapped["FileModel"] = relationship(
        "FileModel",
        viewonly=True,
        lazy="select",
        foreign_keys=[file_id],
    )

    def __repr__(self, **_) -> str:
        attrs: dict[str, Any] = {
            "album_id": self.album_id,
            "file_id": self.file_id,
        }

        return super().__repr__(**attrs)
