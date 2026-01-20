from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import String, Text, Uuid

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import UserModel


class NoteModel(BaseModel):
    __tablename__ = "notes"
    __table_args__ = {"comment": "Пользовательские заметки и записки"}

    title: Mapped[str] = mapped_column(
        String(64),
        default="Новая заметка",
        nullable=False,
        comment="Заголовок пользовательской заметки",
    )
    content: Mapped[str] = mapped_column(
        Text(),
        nullable=True,
        comment="Содержимое пользовательской заметки",
    )
    created_by: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="UUID пользователя, загрузившего заметку",
    )

    creator: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="notes",
        viewonly=True,
        lazy="select",
    )

    def __repr__(self, **_) -> str:
        attrs: dict[str, Any] = {
            "title": self.title,
            "content": self.content,
            "created_by": self.created_by,
        }

        return super().__repr__(**attrs)
