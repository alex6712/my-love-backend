from typing import Annotated
from uuid import UUID

from app.core.enums import NoteType
from app.core.filtering import ColumnAlias
from app.core.types import UNIQUE, UNSET, Maybe
from app.schemas.dto.base import (
    BaseCreateDTO,
    BaseFilterManyDTO,
    BaseFilterOneDTO,
    BaseSQLCoreDTO,
    BaseUpdateDTO,
)
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


class FilterOneNoteDTO(BaseFilterOneDTO):
    """DTO для поиска одной заметки по идентификатору или типу.

    Требует передачи хотя бы одного из уникальных полей: `id` или `type`.
    Используется в сервисах, где заметку можно найти по её идентификатору или по типу.

    Attributes
    ----------
    id : Maybe[UUID]
        Идентификатор заметки. Является уникальным полем - достаточно передать
        только его для однозначного нахождения записи.
    types : Maybe[list[NoteType]]
        Список типов заметок. Используется для фильтрации по типу.
    """

    id: Annotated[Maybe[UUID], UNIQUE] = UNSET

    types: Annotated[Maybe[list[NoteType]], ColumnAlias("type")] = UNSET


class FilterManyNotesDTO(BaseFilterManyDTO):
    """DTO для фильтрации множества заметок.

    Все поля опциональны - пустой DTO возвращает все записи.
    При передаче нескольких полей условия комбинируются через AND.

    Attributes
    ----------
    ids : Maybe[list[UUID]]
        Список идентификаторов заметок.
    types : Maybe[list[NoteType]]
        Список типов заметок.
    """

    ids: Annotated[Maybe[list[UUID]], ColumnAlias("id")] = UNSET
    types: Annotated[Maybe[list[NoteType]], ColumnAlias("type")] = UNSET


class CreateNoteDTO(BaseCreateDTO):
    """DTO для создания новой заметки.

    Attributes
    ----------
    type : NoteType
        Тип заметки.
    title : str
        Заголовок заметки.
    content : str
        Содержание заметки.
    created_by : UUID
        Идентификатор создателя заметки.
    """

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
