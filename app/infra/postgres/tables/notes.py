from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy.types import Enum as SAEnum
from sqlalchemy.types import String, Text, Uuid

from app.core.enums import NoteType
from app.infra.postgres.tables import base_columns, metadata

notes_table = Table(
    "notes",
    metadata,
    *base_columns(),
    Column(
        "type",
        SAEnum(
            NoteType,
            name="note_type",
            native_enum=True,
        ),
        nullable=False,
        index=True,
        comment="Тип пользовательской заметки",
    ),
    Column(
        "title",
        String(64),
        default="Новая заметка",
        nullable=False,
        comment="Заголовок пользовательской заметки",
    ),
    Column(
        "content",
        Text(),
        nullable=True,
        comment="Содержимое пользовательской заметки",
    ),
    Column(
        "created_by",
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="UUID пользователя, загрузившего заметку",
    ),
    comment="Пользовательские заметки и записки",
)
