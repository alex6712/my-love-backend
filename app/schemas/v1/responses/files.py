from pydantic import Field

from app.schemas.dto.file import FileDTO
from app.schemas.v1.responses.standard import PaginationResponse


class FilesResponse(PaginationResponse):
    """Модель ответа сервера с вложенным списком файлов.

    Используется в качестве ответа с сервера на запрос о получении
    файлов пользователем.

    Attributes
    ----------
    files : list[AlbumDTO]
        Список всех файлов, подходящих под фильтры.
    """

    files: list[FileDTO] = Field(
        description="Список всех файлов, подходящих под фильтры.",
    )
