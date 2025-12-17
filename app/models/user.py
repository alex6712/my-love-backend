from uuid import UUID, uuid4

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Boolean, String, Uuid

from app.models.base import BaseModel


class UserModel(BaseModel):
    __tablename__ = "users"
    __table_args__ = {"comment": "Аутентифицированные пользователи системы"}

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        default=uuid4,
        primary_key=True,
        comment="Уникальный идентификатор пользователя",
    )

    username: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        comment="Уникальный логин (макс. 64 символа)",
    )

    password_hash: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Хеш пароля (Argon2id через Passlib)",
    )

    refresh_token_hash: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
        comment="Хеш токена обновления (Argon2id)",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean(),
        default=False,
        nullable=False,
        index=True,
        comment="Статус пользователя (активный или заблокирован)",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username})>"
