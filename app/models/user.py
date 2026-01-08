from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Boolean, String

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.album import AlbumModel
    from app.models.couple import CoupleRequestModel
    from app.models.file import FileModel


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
        default=True,
        nullable=False,
        index=True,
        comment="Статус пользователя (активный или заблокирован)",
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

    async def get_partner(self) -> "UserModel | None":
        if await self.awaitable_attrs.couples_as_initiator:
            couple: CoupleRequestModel = (
                await self.awaitable_attrs.couples_as_initiator
            )[0]

            return await couple.awaitable_attrs.initiator

        if await self.awaitable_attrs.couples_as_recipient:
            couple: CoupleRequestModel = (
                await self.awaitable_attrs.couples_as_recipient
            )[0]

            return await couple.awaitable_attrs.recipient

        return None

    def __repr__(self, **_) -> str:
        attrs: dict[str, Any] = {
            "username": self.username,
            "avatar_url": self.avatar_url,
            "is_active": self.is_active,
        }

        return super().__repr__(**attrs)
