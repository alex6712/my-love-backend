from sqlalchemy import Column, ForeignKey, Table, UniqueConstraint
from sqlalchemy.types import Uuid

from app.infra.postgres.tables import base_columns, metadata

album_items_table = Table(
    "albums",
    metadata,
    *base_columns(),
    Column(
        "album_id",
        Uuid(as_uuid=True),
        ForeignKey("albums.id", ondelete="CASCADE"),
        nullable=False,
        comment="UUID медиа альбома",
    ),
    Column(
        "file_id",
        Uuid(as_uuid=True),
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        comment="UUID медиа файла",
    ),
    UniqueConstraint("album_id", "file_id", name="uq_album_file"),
    comment="Таблица с записями о сохранённых в альбомах медиа",
)
