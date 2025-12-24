from typing import TYPE_CHECKING, Any, List
from uuid import UUID, uuid4

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Boolean, String, Uuid

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.album import AlbumModel
    from app.models.couple import CoupleModel


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
        default=True,
        nullable=False,
        index=True,
        comment="Статус пользователя (активный или заблокирован)",
    )

    couples_as_partner1: Mapped[list["CoupleModel"]] = relationship(
        "CoupleModel",
        foreign_keys="CoupleModel.partner1_id",
        viewonly=True,
        lazy="select",
    )
    couples_as_partner2: Mapped[list["CoupleModel"]] = relationship(
        "CoupleModel",
        foreign_keys="CoupleModel.partner2_id",
        viewonly=True,
        lazy="select",
    )
    media_albums: Mapped[List["AlbumModel"]] = relationship(
        "AlbumModel",
        back_populates="creator",
        lazy="select",
    )

    async def get_partner(self) -> "UserModel | None":
        if await self.awaitable_attrs.couples_as_partner1:
            couple: CoupleModel = (await self.awaitable_attrs.couples_as_partner1)[0]

            return await couple.awaitable_attrs.partner2

        if await self.awaitable_attrs.couples_as_partner2:
            couple: CoupleModel = (await self.awaitable_attrs.couples_as_partner2)[0]

            return await couple.awaitable_attrs.partner1

        return None

    def __repr__(self, **_) -> str:
        attrs: dict[str, Any] = {
            "id": self.id,
            "username": self.username,
            "avatar_url": self.avatar_url,
            "is_active": self.is_active,
        }

        return super().__repr__(**attrs)
