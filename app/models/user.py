from typing import Any, List, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Boolean, String, Uuid

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.album import AlbumModel


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

    avatar_url: Mapped[str] = mapped_column(
        String(512),
        nullable=True,
        comment="URL аватара пользователя",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean(),
        default=False,
        nullable=False,
        index=True,
        comment="Статус пользователя (активный или заблокирован)",
    )

    media_albums: Mapped[List["AlbumModel"]] = relationship(
        "AlbumModel",
        back_populates="creator",
        lazy="select",
    )

    def __repr__(self, **_) -> str:
        attrs: dict[str, Any] = {
            "id": self.id,
            "username": self.username,
            "avatar_url": self.avatar_url,
        }

        return super().__repr__(**attrs)
