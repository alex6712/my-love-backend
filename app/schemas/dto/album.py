from datetime import datetime
from uuid import UUID

from app.schemas.dto.base import BaseDTO
from app.schemas.dto.media import MediaDTO
from app.schemas.dto.users import CreatorDTO


class AlbumDTO(BaseDTO):
    """DTO для представления медиа альбома.

    Attributes
    ----------
    id : UUID
        Уникальный идентификатор медиа альбома.
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
    created_at : datetime
        Временная метка создания альбома.
    """

    id: UUID
    title: str
    description: str | None
    cover_url: str | None
    is_private: bool

    creator: CreatorDTO

    created_at: datetime


class AlbumWithItemsDTO(AlbumDTO):
    """DTO для представления подробной информации о медиа-альбоме.

    Наследуется от `AlbumDTO` и добавляет атрибут `items`,
    в котором сохранены все медиа-файлы, добавленные в
    медиа-альбом.

    Attributes
    ----------
    items : list[MediaDTO]
        Все добавленные в альбом медиа-файлы.
    """

    items: list[MediaDTO]
