from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Boolean, String

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.album import AlbumModel
    from app.models.couple_request import CoupleRequestModel
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
        comment="Хеш пароля (Argon2id через Passlib)",
    )
    avatar_url: Mapped[str] = mapped_column(
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
        lazy="select",
    )
    couples_as_initiator: Mapped[list["CoupleRequestModel"]] = relationship(
        "CoupleRequestModel",
        foreign_keys="CoupleRequestModel.initiator_id",
        viewonly=True,
        lazy="select",
    )
    couples_as_recipient: Mapped[list["CoupleRequestModel"]] = relationship(
        "CoupleRequestModel",
        foreign_keys="CoupleRequestModel.recipient_id",
        viewonly=True,
        lazy="select",
    )
    media_albums: Mapped[list["AlbumModel"]] = relationship(
        "AlbumModel",
        back_populates="creator",
        viewonly=True,
        lazy="select",
    )
    media_files: Mapped[list["FileModel"]] = relationship(
        "FileModel",
        back_populates="creator",
        viewonly=True,
        lazy="select",
    )
    notes: Mapped[list["NoteModel"]] = relationship(
        "NoteModel",
        back_populates="creator",
        viewonly=True,
        lazy="select",
    )

    def __repr__(self, **_) -> str:
        attrs: dict[str, Any] = {
            "username": self.username,
            "avatar_url": self.avatar_url,
            "is_active": self.is_active,
        }

        return super().__repr__(**attrs)
