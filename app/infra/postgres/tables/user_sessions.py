from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy.types import DateTime, String, Uuid

from app.infra.postgres.tables import base_columns, metadata

user_sessions_table = Table(
    "user_sessions",
    metadata,
    *base_columns(),
    Column(
        "user_id",
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="Уникальный идентификатор пользователя",
    ),
    Column(
        "refresh_token_hash",
        String(128),
        nullable=False,
        index=True,
        comment="Хэш токена обновления (HMAC-SHA256)",
    ),
    Column(
        "expires_at",
        DateTime(timezone=True),
        nullable=False,
        comment="Дата и время, когда токен будет просрочен",
    ),
    Column(
        "last_used_at",
        DateTime(timezone=True),
        nullable=False,
        comment="Дата и время последнего обновления сессии",
    ),
    comment="Информация о пользовательских сессиях",
)
