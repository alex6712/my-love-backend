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

    def __repr__(self, **kwargs: Any) -> str:
        values = [f"id={self.id}"]
        values.extend(f"{key}={value}" for key, value in kwargs.items())
        values.append(f"created_at={self.created_at}")

        attributes = ", ".join(values)
        return f"<{self.__class__.__name__}({attributes})>"
