from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Table,
    UniqueConstraint,
)
from sqlalchemy.types import SmallInteger, Uuid

from app.infra.postgres.tables import base_columns, metadata

couple_members_table = Table(
    "couple_members",
    metadata,
    *base_columns(),
    Column(
        "couple_id",
        Uuid(as_uuid=True),
        ForeignKey("couples.id", ondelete="CASCADE"),
        nullable=False,
        comment="UUID пары",
    ),
    Column(
        "user_id",
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="UUID пользователя",
    ),
    Column(
        "slot",
        SmallInteger,
        nullable=False,
        comment="Слот пользователя: 1 или 2",
    ),
    UniqueConstraint("user_id", name="uq_one_couple_per_user"),
    UniqueConstraint("couple_id", "slot", name="uq_couple_slot"),
    CheckConstraint("slot IN (1, 2)", name="ck_slot_values"),
    comment="Таблица с записями о состоящих в парах пользователях",
)
