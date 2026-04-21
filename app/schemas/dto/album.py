from app.core.types import UNSET, Maybe
from app.schemas.dto.base import BaseCreateDTO, BaseSQLCoreDTO, BaseUpdateDTO
from app.schemas.dto.file import FileDTO
from app.schemas.dto.user import CreatorDTO


class AlbumDTO(BaseSQLCoreDTO):
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


class CreateAlbumDTO(BaseCreateDTO):
    title: str
    description: str | None
    cover_url: str | None
    is_private: bool


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
