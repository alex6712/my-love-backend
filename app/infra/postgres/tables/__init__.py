from datetime import datetime
from uuid import UUID

from sqlalchemy import Column, MetaData, text
from sqlalchemy.types import DateTime, Uuid

from app.infra.postgres.tables.couple_members import couple_members_table
from app.infra.postgres.tables.couple_requests import couple_requests_table
from app.infra.postgres.tables.couples import couples_table
from app.infra.postgres.tables.users import users_table

metadata = MetaData()
"""Глобальный реестр всех таблиц SQLAlchemy Core приложения.

Используется как единая точка сбора табличных метаданных.
Передаётся в каждую `Table(...)` в качестве второго аргумента,
а также используется при создании и удалении схемы БД
(например, `metadata.create_all(engine)`).

Notes
-----
Должен существовать в единственном экземпляре на всё приложение.
Повторное создание `MetaData()` в других модулях приведёт к тому,
что зарегистрированные в них таблицы будут недоступны из этого объекта.
"""


def base_columns() -> tuple[Column[UUID], Column[datetime]]:
    """Создать базовые колонки, общие для всех таблиц приложения.

    Каждый вызов возвращает новые объекты `Column`, что необходимо,
    так как SQLAlchemy привязывает колонку к конкретной таблице
    при её первом использовании.

    Returns
    -------
    tuple[Column[UUID], Column[datetime]]
        Кортеж из двух колонок:

        - **id** : `UUID`, primary key.
            Генерируется на стороне БД через `gen_random_uuid()`.
        - **created_at** : `datetime` (timezone-aware), not null.
            Устанавливается на стороне БД в момент вставки строки
            через `TIMEZONE('UTC', NOW())`.
    """
    return (
        Column(
            "id",
            Uuid(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
            comment="Уникальный идентификатор записи",
        ),
        Column(
            "created_at",
            DateTime(timezone=True),
            nullable=False,
            server_default=text("TIMEZONE('UTC', NOW())"),
            comment="Дата и время создания записи",
        ),
    )


__all__ = [
    "metadata",
    "base_columns",
    "couple_members_table",
    "couple_requests_table",
    "couples_table",
    "users_table",
]
