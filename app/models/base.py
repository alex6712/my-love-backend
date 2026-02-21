from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import DateTime, Uuid


class BaseModel(AsyncAttrs, DeclarativeBase):
    __abstract__ = True

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        comment="Уникальный идентификатор записи",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("TIMEZONE('UTC', NOW())"),
        comment="Дата и время создания записи",
    )

    def __repr__(self, **kwargs: dict[str, Any]) -> str:
        values: str = "".join(f"{key}={value}, " for key, value in kwargs.items())

        return f"<{self.__class__.__name__}(id={self.id}, {values}created_at={self.created_at})>"
