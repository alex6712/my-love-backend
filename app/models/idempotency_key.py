from typing import Any
from uuid import UUID

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Text, Uuid

from app.models.base import BaseModel


class IdempotencyKeyModel(BaseModel):
    __tablename__ = "idempotency_keys"
    __table_args__ = {
        "comment": "Ключи для обеспечения идемпотентности",
    }

    scope: Mapped[str] = mapped_column(
        Text(),
        nullable=False,
        comment="Область применения ключа (идиоматично namespace)",
    )
    entity_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        comment="UUID записи, относительно которой обеспечивается идемпотентность",
    )

    def __repr__(self, **_) -> str:
        attrs: dict[str, Any] = {
            "scope": self.scope,
            "entity_id": self.entity_id,
        }

        return super().__repr__(**attrs)
