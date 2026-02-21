from app.schemas.dto.base import BaseSQLModelDTO
from app.schemas.dto.file import FileDTO
from app.schemas.dto.user import CreatorDTO


class AlbumDTO(BaseSQLModelDTO):
    """DTO для представления медиа альбома.

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


class AlbumWithItemsDTO(AlbumDTO):
    """DTO для представления подробной информации о медиа-альбоме.

    Наследуется от `AlbumDTO` и добавляет атрибут `items`,
    в котором сохранены все медиа-файлы, добавленные в
    медиа-альбом.

    Attributes
    ----------
    items : list[FileDTO]
        Все добавленные в альбом медиа-файлы.
    total : int
        Общее количество элементов в альбоме.
    """

    items: list[FileDTO]
    total: int
