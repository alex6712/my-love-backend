from datetime import datetime
from uuid import UUID

from sqlalchemy import Column, ForeignKey, MetaData, text
from sqlalchemy.types import DateTime, Uuid

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


def owned_columns() -> tuple[Column[UUID]]:
    """Создать колонки владения сущностью (ownership).

    Добавляет в таблицу ссылку на пользователя-владельца записи.
    Используется для сущностей, доступ к которым ограничен
    их создателем (например, приватные ресурсы).

    Каждый вызов возвращает новый объект `Column`, поскольку
    SQLAlchemy привязывает колонку к конкретной таблице при первом использовании.

    Returns
    -------
    tuple[Column[UUID]]
        Кортеж из одной колонки:

        - **created_by** : `UUID`, foreign key, not null.
            Ссылается на `users.id`. Указывает пользователя,
            создавшего запись.
            При удалении пользователя связанные записи также удаляются
            за счёт `ON DELETE CASCADE`.
    """
    return (
        Column(
            "created_by",
            Uuid(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            comment="UUID пользователя-владельца ресурса",
        ),
    )
