from sqlalchemy import Column, Date, Table

from app.infra.postgres.tables import base_columns, metadata

couples_table = Table(
    "couples",
    metadata,
    *base_columns(),
    Column(
        "relationship_started_on",
        Date,
        nullable=True,
        comment="Реальная дата начала отношений",
    ),
    comment="Сведения о зарегистрированных парах между пользователями в приложении",
)
