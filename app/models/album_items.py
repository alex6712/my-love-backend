from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.types import Uuid

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.album import AlbumModel
    from app.models.media import MediaModel


class AlbumItemsModel(BaseModel):
    __tablename__ = "album_items"
    __table_args__ = {"comment": "Таблица с записями о сохранённых в альбомах медиа."}

    album_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("albums.id", ondelete="CASCADE"),
        primary_key=True,
        comment="UUID медиа альбома",
    )
    media_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("media.id", ondelete="CASCADE"),
        primary_key=True,
        comment="UUID медиа файла",
    )

    album: Mapped["AlbumModel"] = relationship(
        "AlbumModel",
        viewonly=True,
        lazy="select",
        foreign_keys=[album_id],
    )
    media: Mapped["MediaModel"] = relationship(
        "MediaModel",
        viewonly=True,
        lazy="select",
        foreign_keys=[media_id],
    )

    def __repr__(self, **_) -> str:
        attrs: dict[str, Any] = {
            "album_id": self.album_id,
            "media_id": self.media_id,
        }

        return super().__repr__(**attrs)
