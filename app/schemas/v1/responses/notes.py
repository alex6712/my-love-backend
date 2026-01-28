from pydantic import Field

from app.schemas.dto.note import NoteDTO
from app.schemas.v1.responses.standard import StandardResponse


class NotesResponse(StandardResponse):
    """Модель ответа сервера с вложенным списком заметок.

    Используется в качестве ответа с сервера на запрос о получении
    заметок пользователем.

    Attributes
    ----------
    notes : list[NoteDTO]
        Список всех заметок, подходящих под фильтры.
    """

    notes: list[NoteDTO] = Field(
        description="Список всех заметок, подходящих под фильтры.",
    )
