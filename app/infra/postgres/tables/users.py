from sqlalchemy import Column, Index, Table, UniqueConstraint, text
from sqlalchemy.types import Boolean, String

from app.core.consts import DISPLAY_NAME_MAX_LENGTH, USERNAME_MAX_LENGTH
from app.infra.postgres.tables import base_columns, metadata

users_table = Table(
    "users",
    metadata,
    *base_columns(),
    Column(
        "username",
        String(USERNAME_MAX_LENGTH),
        nullable=False,
        comment=f"Уникальный логин (макс. {USERNAME_MAX_LENGTH} символа)",
    ),
    Column(
        "password_hash",
        String(128),
        nullable=False,
        comment="Хэш пароля (Argon2id через Passlib)",
    ),
    Column(
        "display_name",
        String(DISPLAY_NAME_MAX_LENGTH),
        nullable=False,
        comment=f"Отображаемое имя пользователя (макс. {DISPLAY_NAME_MAX_LENGTH} символов)",
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
