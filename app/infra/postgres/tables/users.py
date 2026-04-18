from sqlalchemy import Boolean, Column, Index, String, Table, UniqueConstraint, text

from app.infra.postgres.tables import base_columns, metadata

users_table = Table(
    "users",
    metadata,
    *base_columns(),
    Column(
        "username",
        String(64),
        nullable=False,
        comment="Уникальный логин (макс. 64 символа)",
    ),
    Column(
        "password_hash",
        String(128),
        nullable=False,
        comment="Хэш пароля (Argon2id через Passlib)",
    ),
    Column(
        "avatar_url",
        String(512),
        nullable=True,
        comment="URL аватара пользователя",
    ),
    Column(
        "is_active",
        Boolean(),
        nullable=False,
        server_default=text("true"),
        comment="Статус пользователя (активный или заблокирован)",
    ),
    UniqueConstraint("username", name="uq_users_username"),
    Index("ix_users_username", "username"),
    Index("ix_users_is_active", "is_active"),
    comment="Аутентифицированные пользователи системы",
)
