from pydantic import Field

from app.schemas.dto.album import AlbumDTO, AlbumWithItemsDTO
from app.schemas.v1.responses.standard import PaginationResponse, StandardResponse


class AlbumResponse(StandardResponse):
    """Модель ответа сервера с вложенной информацией о медиа-альбоме.

    Используется в качестве ответа сервера на запрос о конкретном
    альбоме.

    Обычно это означает, что запрашиваемая информация
    будет выводиться в окне просмотра альбома, поэтому возвращаемый DTO
    также содержит информацию и обо всех входящих в альбом медиа-файлах.

    Attributes
    ----------
    album : AlbumWithItemsDTO
        Подробный DTO медиа альбома.
    """

    album: AlbumWithItemsDTO = Field(
        description="Подробная информация о медиа-альбоме.",
    )


class AlbumsResponse(PaginationResponse):
    """Модель ответа сервера с вложенным списком альбомов.

    Используется в качестве ответа с сервера на запрос о получении
    альбомов пользователем.

    Attributes
    ----------
    albums : list[AlbumDTO]
        Список всех альбомов, подходящих под фильтры.
    """

    albums: list[AlbumDTO] = Field(
        description="Список всех альбомов, подходящих под фильтры.",
    )
