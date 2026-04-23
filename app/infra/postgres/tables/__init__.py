import importlib
import pkgutil
from datetime import datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import Column, ForeignKey, MetaData, Table, text
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


"""Автоматический импорт таблиц SQLAlchemy для Alembic-миграций.

Следующий код обеспечивает автоматическое обнаружение и регистрацию всех таблиц,
что необходимо для корректной работы Alembic.

При импорте данного модуля происходит сканирование всех Python-файлов
в текущем каталоге и автоматический импорт определённых в них таблиц.

Notes
-----
Принцип работы:
1. Сканирование текущего каталога на наличие таблиц `sqlalchemy.Table`;
2. Исключение специальных файлов (`__init__.py`);
3. Динамический импорт каждого обнаруженного модуля;
4. Поиск в модуле объектов, являющихся объектами `Table`;
5. Добавление найденных объектов в глобальное пространство имён.

Это позволяет Alembic автоматически видеть все таблицы без необходимости
явного импорта каждой из них в `__init__.py`. При добавлении новой таблицы
достаточно создать файл с объектом класса Table, и он будет
обнаружен при следующем запуске.
"""

package_dir = Path(__file__).resolve().parent
modules = pkgutil.iter_modules([str(package_dir)])

for _, module_name, is_pkg in modules:
    if module_name == "__init__" or is_pkg:
        continue

    module = importlib.import_module(f".{module_name}", package=__package__)

    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if isinstance(attr, Table):
            globals()[attr_name] = attr

__all__ = [name for name in globals() if not name.startswith("_")]  # type: ignore
