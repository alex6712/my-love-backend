from app.core.enums import NoteType
from app.schemas.dto.base import BaseSQLModelDTO
from app.schemas.dto.users import CreatorDTO


class NoteDTO(BaseSQLModelDTO):
    """DTO для представления пользовательских заметок.

    Attributes
    ----------
    type : NoteType
        Тип пользовательской заметки.
    title : str
        Заголовок пользовательской заметки.
    content : str
        Тест пользовательской заметки.
    creator : CreatorDTO
        DTO пользователя, создавшего заметку.
    """

    type: NoteType
    title: str
    content: str

    creator: CreatorDTO
