from datetime import datetime
from typing import Any
from uuid import UUID

from app.models.file import FileType
from app.schemas.dto.base import BaseDTO
from app.schemas.dto.users import CreatorDTO


class FileDTO(BaseDTO):
    """DTO для представления медиа-файла.

    Attributes
    ----------
    id : UUID
        Уникальный идентификатор медиа-файла.
    object_key : str
        Путь до файла внутри бакета приложения.
    type_ : FileType
        Тип сохранённого медиа-файла:
        - 'image' - изображение;
        - 'video' - видеофайл.
    title : str
        Наименование медиа-файла.
    description : str | None
        Описание медиа-файла.
    geo_data : dict[str, Any] | None
        Данные о местоположении сохранённого медиа
    creator : CreatorDTO
        DTO пользователя, создавшего медиа-файл.
    created_at : datetime
        Временная метка создания медиа-файла.
    """

    id: UUID
    object_key: str
    type_: FileType
    title: str
    description: str | None
    geo_data: dict[str, Any] | None

    creator: CreatorDTO

    created_at: datetime
