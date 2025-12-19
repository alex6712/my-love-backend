from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime, text


class BaseModel(AsyncAttrs, DeclarativeBase):
    __abstract__ = True

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("TIMEZONE('UTC', NOW())"),
        nullable=False,
        comment="Дата и время создания записи.",
    )

    def __repr__(self, **kwargs: dict[str, Any]) -> str:
        values: str = "".join(f"{key}={value}, " for key, value in kwargs.items())

        return f"<{self.__class__.__name__}({values}created_at={self.created_at})>"
