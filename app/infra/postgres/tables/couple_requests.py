from textwrap import dedent

from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Table,
    text,
)
from sqlalchemy.types import DateTime, Uuid
from sqlalchemy.types import Enum as SAEnum

from app.core.enums import CoupleRequestStatus
from app.infra.postgres.tables import base_columns, metadata

couple_requests_table = Table(
    "couple_requests",
    metadata,
    *base_columns(),
    Column(
        "initiator_id",
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="UUID пользователя-инициатора",
    ),
    Column(
        "recipient_id",
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="UUID пользователя-реципиента",
    ),
    Column(
        "status",
        SAEnum(CoupleRequestStatus, name="couple_request_status", native_enum=True),
        nullable=False,
        server_default=text("'PENDING'"),
        comment="Статус запроса на создание пары",
    ),
    Column(
        "accepted_at",
        DateTime(timezone=True),
        nullable=True,
        comment="Дата и время принятия приглашения",
    ),
    CheckConstraint("initiator_id <> recipient_id", name="ck_couple_not_self"),
    CheckConstraint(
        dedent("""
            (status = 'ACCEPTED' AND accepted_at IS NOT NULL)
            OR
            (status != 'ACCEPTED' AND accepted_at IS NULL)
        """).strip(),
        name="ck_accepted_at_consistency",
    ),
    Index(
        "uq_couple_request_pending",
        text("LEAST(initiator_id, recipient_id)"),
        text("GREATEST(initiator_id, recipient_id)"),
        unique=True,
        postgresql_where=text("status = 'PENDING'"),
    ),
    Index(
        "ix_couple_request_recipient_status",
        "recipient_id",
        postgresql_where=text("status = 'PENDING'"),
    ),
    Index(
        "ix_couple_request_initiator_status",
        "initiator_id",
        postgresql_where=text("status = 'PENDING'"),
    ),
    comment="Сведения о запросах на создание пар между пользователями в приложении",
)
