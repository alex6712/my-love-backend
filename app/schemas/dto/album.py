from typing import Annotated, TypeVar
from uuid import UUID

from app.core.filtering import ColumnAlias
from app.core.types import UNIQUE, UNSET, Maybe
from app.schemas.dto.base import (
    BaseCreateDTO,
    BaseFilterManyDTO,
    BaseFilterOneDTO,
    BaseSearchDTO,
    BaseSQLCoreDTO,
    BaseUpdateDTO,
)
from app.schemas.dto.file import InternalFileDTO, PublicFileDTO
from app.schemas.dto.user import CreatorDTO

T = TypeVar("T", bound=PublicFileDTO)


class AlbumDTO(BaseSQLCoreDTO):
    """DTO для представления медиаальбома.

    Attributes
    ----------
    title : str
        Наименование альбома.
    description : str | None
        Описание альбома.
    cover_url : str | None
        URL обложки альбома.
    is_private : bool
        Видимость альбома (True - личный или False - публичный).
    creator : CreatorDTO
        DTO пользователя, создавшего альбом.
    """

    title: str
    description: str | None
    cover_url: str | None
    is_private: bool

    creator: CreatorDTO


class AlbumWithItemsDTO[T](AlbumDTO):
    """DTO для представления подробной информации о медиаальбоме.

    Наследуется от `AlbumDTO` и добавляет атрибут `items`,
    в котором сохранены все медиафайлы, добавленные в
    медиаальбом, а также `total` - общее количество
    элементов.

    Attributes
    ----------
    items : list[T]
        Все добавленные в альбом медиафайлы.
    total : int
        Общее количество элементов в альбоме.
    """

    items: list[T]
    total: int


PublicAlbumWithItemsDTO = AlbumWithItemsDTO[PublicFileDTO]
"""Публичный DTO альбома с вложенными медиафайлами, который сериализуется в API-ответах."""

InternalAlbumWithItemsDTO = AlbumWithItemsDTO[InternalFileDTO]
"""Внутренний DTO альбома с вложенными медиафайлами, который используется в сервисах и репозиториях."""


class FilterOneAlbumDTO(BaseFilterOneDTO):
    """DTO для поиска одного альбома по идентификатору.

    Требует передачи уникального поля `id` для однозначного
    нахождения записи.

    Attributes
    ----------
    id : Maybe[UUID]
        Идентификатор альбома. Является уникальным полем - достаточно
        передать только его для однозначного нахождения записи.
    is_private : Maybe[bool]
        Признак приватности альбома. Используется как дополнительный
        фильтр при поиске.
    """

    id: Annotated[Maybe[UUID], UNIQUE] = UNSET

    is_private: Maybe[bool] = UNSET


class FilterManyAlbumsDTO(BaseFilterManyDTO):
    """DTO для фильтрации множества альбомов.

    Все поля опциональны - пустой DTO возвращает все записи.
    При передаче нескольких полей условия комбинируются через AND.

    Attributes
    ----------
    ids : Maybe[list[UUID]]
        Список идентификаторов альбомов.
    is_private : Maybe[bool]
        Признак приватности альбома.
    """

    ids: Annotated[Maybe[list[UUID]], ColumnAlias("id")] = UNSET
    is_private: Maybe[bool] = UNSET


class SearchAlbumDTO(BaseSearchDTO):
    """DTO для полнотекстового поиска альбомов.

    Расширяет `BaseSearchDTO` порогом релевантности, позволяя
    отсекать результаты с низким совпадением.

    Attributes
    ----------
    threshold : float
        Минимальный порог релевантности результата. Записи с оценкой
        ниже порога исключаются из выборки.
    """

    threshold: float


class CreateAlbumDTO(BaseCreateDTO):
    """DTO для создания нового медиаальбома.

    Attributes
    ----------
    title : str
        Наименование альбома.
    description : str | None
        Описание альбома.
    cover_url : str | None
        URL обложки альбома.
    is_private : bool
        Видимость альбома (True - личный, False - публичный).
    created_by : UUID
        Идентификатор создателя файла.

    Notes
    -----
    Поле `creator` не передаётся, так как определяется
    на основе контекста аутентификации (например, из JWT).
    """

    title: str
    description: str | None
    cover_url: str | None
    is_private: bool
    created_by: UUID


class UpdateAlbumDTO(BaseUpdateDTO):
    """DTO для частичного обновления альбома.

    Attributes
    ----------
    title : Maybe[str]
        Новое наименование альбома. Если `UNSET`- поле не изменяется.
    description : Maybe[str | None]
        Новое описание альбома. Если `UNSET`- поле не изменяется.
        Может быть явно передано как None для удаления описания.
    cover_url : Maybe[str | None]
        Новая URL обложки альбома. Если `UNSET`- поле не изменяется.
        Может быть явно передана как None для удаления обложки.
    is_private : Maybe[bool]
        Видимость альбома (True - личный, False - публичный).
        Если `UNSET`- поле не изменяется.
    """

    title: Maybe[str] = UNSET
    description: Maybe[str | None] = UNSET
    cover_url: Maybe[str | None] = UNSET
    is_private: Maybe[bool] = UNSET
