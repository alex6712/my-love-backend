from pydantic import Field

from app.schemas.dto.album import AlbumDTO, PublicAlbumWithItemsDTO
from app.schemas.v1.responses.standard import PaginationResponse, StandardResponse


class AlbumResponse(StandardResponse):
    """Модель ответа сервера с вложенной информацией о медиаальбоме.

    Используется в качестве ответа сервера на запрос о конкретном
    альбоме.

    Обычно это означает, что запрашиваемая информация
    будет выводиться в окне просмотра альбома, поэтому возвращаемый DTO
    также содержит информацию и обо всех входящих в альбом медиафайлах.

    Attributes
    ----------
    album : PublicAlbumWithItemsDTO
        Подробный DTO медиаальбома.
    """

    album: PublicAlbumWithItemsDTO = Field(
        description="Подробная информация о медиаальбоме.",
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
