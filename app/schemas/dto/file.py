from typing import Any
from uuid import UUID

from app.core.enums import DownloadFileErrorCode, FileStatus, UploadFileErrorCode
from app.core.types import UNSET, Maybe
from app.schemas.dto.base import (
    BaseCreateDTO,
    BaseDTO,
    BaseErrorDTO,
    BaseSQLCoreDTO,
    BaseUpdateDTO,
)
from app.schemas.dto.user import CreatorDTO


class InternalFileMetadataDTO(BaseDTO):
    """Базовое DTO для представления метаданных медиа-файла.

    Attributes
    ----------
    content_type : str
        Тип сохранённого медиа-файла.
    title : str
        Наименование медиа-файла.
    description : str | None
        Описание медиа-файла.
    geo_data : dict[str, Any] | None, optional
        Данные о местоположении сохранённого медиа
    """

    content_type: str
    title: str
    description: str | None
    geo_data: dict[str, Any] | None = None


class FileMetadataDTO(InternalFileMetadataDTO):
    """DTO для представления метаданных медиа-файла.

    Attributes
    ----------
    client_ref_id: str
        Произвольный клиентский идентификатор для корреляции результата.
    """

    client_ref_id: str


class FileDTO(BaseSQLCoreDTO, InternalFileMetadataDTO):
    """DTO для представления медиа-файла.

    Attributes
    ----------
    object_key : str
        Путь до файла внутри бакета приложения.
    status : FileStatus
        Текущий статус медиа-файла.
    creator : CreatorDTO
        DTO пользователя, создавшего медиа-файл.
    """

    object_key: str
    status: FileStatus

    creator: CreatorDTO


class CreateFileDTO(BaseCreateDTO, InternalFileMetadataDTO):
    """DTO для создания нового файла.

    Объединяет базовые поля создания сущности (`BaseCreateDTO`)
    и метаданные медиа-файла (`InternalFileMetadataDTO`).
    Также содержит информацию, необходимую для доступа к
    объекту в файловом хранилище.

    Attributes
    ----------
    object_key : str
        Уникальный ключ объекта в файловом хранилище.
    status : FileStatus
        Статус создаваемой записи медиа-файла.
    """

    object_key: str
    status: FileStatus


class UpdateFileDTO(BaseUpdateDTO):
    """DTO для частичного обновления медиа-файла.

    Attributes
    ----------
    status : FileStatus
        Новый статус медиа-файла. Если `UNSET`- поле не изменяется.
    title : Maybe[str]
        Новое наименование файла. Если `UNSET`- поле не изменяется.
    description : Maybe[str | None]
        Новое описание файла. Если `UNSET`- поле не изменяется.
        Может быть явно передано как None для удаления описания.
    """

    status: Maybe[FileStatus] = UNSET
    title: Maybe[str] = UNSET
    description: Maybe[str | None] = UNSET


class DownloadFileErrorDTO(BaseErrorDTO[DownloadFileErrorCode]):
    """DTO для представления ошибки при скачивании файла.

    Расширяет :class:`BaseErrorDTO`, фиксируя тип кода ошибки как
    :class:`DownloadFileErrorCode` и добавляя идентификатор файла,
    при обработке которого возникла ошибка.

    Attributes
    ----------
    file_id : UUID
        Идентификатор файла, скачивание которого завершилось ошибкой.
    """

    file_id: UUID


class UploadFileErrorDTO(BaseErrorDTO[UploadFileErrorCode]):
    """DTO для представления ошибки при загрузке файла.

    Расширяет :class:`BaseErrorDTO`, фиксируя тип кода ошибки как
    :class:`UploadFileErrorCode` и добавляя клиентский идентификатор файла,
    при обработке которого возникла ошибка.

    Attributes
    ----------
    client_ref_id : str
        Клиентский идентификатор файла, загрузка которого завершилась ошибкой.
    """

    client_ref_id: str
