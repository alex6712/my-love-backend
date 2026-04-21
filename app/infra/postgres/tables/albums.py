from sqlalchemy import Column, Index, Table
from sqlalchemy.types import Boolean, String, Text

from app.infra.postgres.tables import base_columns, metadata, owned_columns

albums_table = Table(
    "albums",
    metadata,
    *base_columns(),
    Column(
        "title",
        String(64),
        default="Новый альбом",
        nullable=False,
        comment="Наименование альбома",
    ),
    Column(
        "description",
        Text(),
        nullable=True,
        comment="Описание альбома",
    ),
    Column(
        "cover_url",
        String(512),
        nullable=True,
        comment="URL обложки альбома",
    ),
    Column(
        "is_private",
        Boolean(),
        default=False,
        nullable=False,
        index=True,
        comment="Видимость альбома (личный или публичный)",
    ),
    *owned_columns(),
    Index(
        "idx_album_title_trgm",
        "title",
        postgresql_using="gin",
        postgresql_ops={"title": "gin_trgm_ops"},
    ),
    Index(
        "idx_album_description_trgm",
        "description",
        postgresql_using="gin",
        postgresql_ops={"description": "gin_trgm_ops"},
    ),
    comment="Созданные пользователями альбомы медиа",
)
