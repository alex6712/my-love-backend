from uuid import UUID

from app.core.enums import NoteType
from app.core.types import UNSET, Maybe
from app.schemas.dto.base import BaseCreateDTO, BaseSQLCoreDTO, BaseUpdateDTO
from app.schemas.dto.user import CreatorDTO


class NoteDTO(BaseSQLCoreDTO):
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


class CreateNoteDTO(BaseCreateDTO):
    type: NoteType
    title: str
    content: str
    created_by: UUID


class UpdateNoteDTO(BaseUpdateDTO):
    """DTO для частичного обновления заметки.

    Attributes
    ----------
    title : Maybe[str]
        Новый заголовок заметки. Если `UNSET` - поле не изменяется.
    content : Maybe[str]
        Новое содержание заметки. Если `UNSET` - поле не изменяется.
    """

    title: Maybe[str] = UNSET
    content: Maybe[str] = UNSET
