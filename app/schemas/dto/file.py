from typing import Any

from app.core.enums import FileStatus
from app.core.types import UNSET, Maybe
from app.schemas.dto.base import BaseDTO, BasePatchDTO, BaseSQLModelDTO
from app.schemas.dto.user import CreatorDTO


class FileMetadataDTO(BaseDTO):
    """DTO для представления метаданных медиа-файла.

    Attributes
    ----------
    content_type : str
        Тип сохранённого медиа-файла.
    title : str
        Наименование медиа-файла.
    description : str | None
        Описание медиа-файла.
    """

    content_type: str
    title: str
    description: str | None


class FileDTO(BaseSQLModelDTO, FileMetadataDTO):
    """DTO для представления медиа-файла.

    Attributes
    ----------
    object_key : str
        Путь до файла внутри бакета приложения.
    status : FileStatus
        Текущий статус медиа-файла.
    geo_data : dict[str, Any] | None
        Данные о местоположении сохранённого медиа
    creator : CreatorDTO
        DTO пользователя, создавшего медиа-файл.
    """

    object_key: str
    status: FileStatus
    geo_data: dict[str, Any] | None

    creator: CreatorDTO


class PatchFileDTO(BasePatchDTO):
    """DTO для частичного обновления медиа-файла.

    Attributes
    ----------
    title : Maybe[str]
        Новое наименование файла. Если `UNSET`- поле не изменяется.
    description : Maybe[str | None]
        Новое описание файла. Если `UNSET`- поле не изменяется.
        Может быть явно передано как None для удаления описания.
    """

    title: Maybe[str] = UNSET
    description: Maybe[str | None] = UNSET
