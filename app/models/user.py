from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Boolean, String

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.album import AlbumModel
    from app.models.couple import CoupleModel
    from app.models.file import FileModel
    from app.models.note import NoteModel
    from app.models.user_session import UserSessionModel


class UserModel(BaseModel):
    __tablename__ = "users"
    __table_args__ = {"comment": "Аутентифицированные пользователи системы"}

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
        comment="Хэш пароля (Argon2id через Passlib)",
    )
    avatar_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        comment="URL аватара пользователя",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean(),
        default=True,
        nullable=False,
        index=True,
        comment="Статус пользователя (активный или заблокирован)",
    )

    sessions: Mapped[list["UserSessionModel"]] = relationship(
        "UserSessionModel",
        back_populates="user",
        viewonly=True,
        lazy="raise",
    )
    couple: Mapped["CoupleModel"] = relationship(
        "CoupleModel",
        secondary="couple_members",
        viewonly=True,
        lazy="raise",
    )
    media_albums: Mapped[list["AlbumModel"]] = relationship(
        "AlbumModel",
        back_populates="creator",
        viewonly=True,
        lazy="raise",
    )
    media_files: Mapped[list["FileModel"]] = relationship(
        "FileModel",
        back_populates="creator",
        viewonly=True,
        lazy="raise",
    )
    notes: Mapped[list["NoteModel"]] = relationship(
        "NoteModel",
        back_populates="creator",
        viewonly=True,
        lazy="raise",
    )

    def __repr__(self, **_) -> str:
        attrs: dict[str, Any] = {
            "username": self.username,
            "avatar_url": self.avatar_url,
            "is_active": self.is_active,
        }

        return super().__repr__(**attrs)
