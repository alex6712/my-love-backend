from pydantic import Field

from app.schemas.dto.album import AlbumDTO
from app.schemas.v1.responses.standard import StandardResponse


class AlbumsResponse(StandardResponse):
    """Модель ответа сервера с вложенным списком альбомов.

    Используется в качестве ответа с сервера на запрос о получении
    альбомов пользователем.

    Attributes
    ----------
    albums : list[AlbumDTO]
        Список всех альбомов, подходящих под фильтры.
    """

    albums: list[AlbumDTO] = Field(
        default=[],
        description="Список всех альбомов, подходящих под фильтры.",
    )
