from typing import Annotated, Any
from uuid import UUID

from app.core.enums import DownloadFileErrorCode, FileStatus, UploadFileErrorCode
from app.core.filtering import ColumnAlias
from app.core.types import UNIQUE, UNSET, Maybe
from app.schemas.dto.base import (
    BaseCreateDTO,
    BaseDTO,
    BaseErrorDTO,
    BaseFilterManyDTO,
    BaseFilterOneDTO,
    BaseSQLCoreDTO,
    BaseUpdateDTO,
)
from app.schemas.dto.user import CreatorDTO


class InternalFileMetadataDTO(BaseDTO):
    """Базовое DTO для представления метаданных медиафайла.

    Attributes
    ----------
    content_type : str
        Тип сохранённого медиафайла.
    title : str
        Наименование медиафайла.
    description : str | None
        Описание медиафайла.
    geo_data : dict[str, Any] | None, optional
        Данные о местоположении сохранённого медиа
    """

    content_type: str
    title: str
    description: str | None
    geo_data: dict[str, Any] | None = None


class FileMetadataDTO(InternalFileMetadataDTO):
    """DTO для представления метаданных медиафайла.

    Attributes
    ----------
    client_ref_id: str
        Произвольный клиентский идентификатор для корреляции результата.
    """

    client_ref_id: str


class PublicFileDTO(BaseSQLCoreDTO, InternalFileMetadataDTO):
    """Публичное DTO для представления медиафайла.

    Attributes
    ----------
    status : FileStatus
        Текущий статус медиафайла.
    creator : CreatorDTO
        DTO пользователя, создавшего медиафайл.
    """

    status: FileStatus

    creator: CreatorDTO


class InternalFileDTO(PublicFileDTO):
    """Внутреннее DTO для представления медиафайла.

    Attributes
    ----------
    object_key : str
        Путь до файла внутри бакета приложения.
    """

    object_key: str


class FilterOneFileDTO(BaseFilterOneDTO):
    """DTO для поиска одной записи файла по идентификатору или объектному ключу.

    Требует передачи хотя бы одного из уникальных полей: `id` или `object_key`.
    Используется в сервисах, где файл можно найти по его идентификатору
    или по уникальному ключу объекта.

    Attributes
    ----------
    id : Maybe[UUID]
        Идентификатор файла. Является уникальным полем - достаточно передать
        только его для однозначного нахождения записи.
    object_key : Maybe[str]
        Объектный ключ файла. Является уникальным полем - достаточно передать
        только его для однозначного нахождения записи.
    statuses : Maybe[list[FileStatus]]
        Список статусов файла. Используется для дополнительной фильтрации.
    """

    id: Annotated[Maybe[UUID], UNIQUE] = UNSET
    object_key: Annotated[Maybe[str], UNIQUE] = UNSET

    statuses: Annotated[Maybe[list[FileStatus]], ColumnAlias("status")] = UNSET


class FilterManyFilesDTO(BaseFilterManyDTO):
    """DTO для фильтрации множества файлов.

    Все поля опциональны - пустой DTO возвращает все записи.
    При передаче нескольких полей условия комбинируются через AND.

    Attributes
    ----------
    ids : Maybe[list[UUID]]
        Список идентификаторов файлов.
    object_keys : Maybe[list[str]]
        Список объектных ключей файлов.
    statuses : Maybe[list[FileStatus]]
        Список статусов файлов.
    """

    ids: Annotated[Maybe[list[UUID]], ColumnAlias("id")] = UNSET
    object_keys: Annotated[Maybe[list[str]], ColumnAlias("object_key")] = UNSET
    statuses: Annotated[Maybe[list[FileStatus]], ColumnAlias("status")] = UNSET


class CreateFileDTO(BaseCreateDTO, InternalFileMetadataDTO):
    """DTO для создания нового файла.

    Объединяет базовые поля создания сущности (`BaseCreateDTO`)
    и метаданные медиафайла (`InternalFileMetadataDTO`).
    Также содержит информацию, необходимую для доступа к
    объекту в файловом хранилище.

    Attributes
    ----------
    id : UUID
        Идентификатор медиафайла.
    object_key : str
        Уникальный ключ объекта в файловом хранилище.
    status : FileStatus
        Статус создаваемой записи медиафайла.
    created_by : UUID
        Идентификатор создателя файла.
    """

    id: UUID
    object_key: str
    status: FileStatus
    created_by: UUID


class UpdateFileDTO(BaseUpdateDTO):
    """DTO для частичного обновления медиафайла.

    Attributes
    ----------
    status : FileStatus
        Новый статус медиафайла. Если `UNSET`- поле не изменяется.
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
