from sqlalchemy import Column, Table
from sqlalchemy.types import JSON, String, Text
from sqlalchemy.types import Enum as SAEnum

from app.core.enums import FileStatus
from app.infra.postgres.tables import base_columns, metadata, owned_columns

files_table = Table(
    "files",
    metadata,
    *base_columns(),
    Column(
        "object_key",
        String(512),
        nullable=False,
        comment="Путь до файла внутри бакета приложения",
    ),
    Column(
        "content_type",
        String(64),
        nullable=False,
        comment="Тип медиафайла",
    ),
    Column(
        "status",
        SAEnum(
            FileStatus,
            name="file_status",
            native_enum=True,
        ),
        default=FileStatus.PENDING,
        nullable=False,
        index=True,
        comment="Текущий статус медиафайла",
    ),
    Column(
        "title",
        String(64),
        default="Новый файл",
        nullable=False,
        comment="Наименование медиафайла",
    ),
    Column(
        "description",
        Text(),
        nullable=True,
        comment="Описание медиафайла",
    ),
    Column(
        "geo_data",
        JSON(),
        default=None,
        nullable=True,
        comment="Данные о местоположении сохранённого медиа",
    ),
    *owned_columns(),
    comment="Загруженные пользователями медиафайлы",
)
