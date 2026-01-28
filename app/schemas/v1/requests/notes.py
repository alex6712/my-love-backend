from pydantic import BaseModel, Field

from app.core.enums import NoteType


class UpdateNoteRequest(BaseModel):
    """Схема запроса на редактирование заметки.

    Используется в качестве представления данных для обновления
    полей пользовательской заметки.

    Attributes
    ----------
    title : str
        Заголовок пользовательской заметки.
    content : str
        Содержание пользовательской заметки.
    """

    title: str = Field(
        default="Новая заметка",
        description="Заголовок пользовательской заметки",
        examples=["Новый телефон"],
    )
    content: str = Field(
        description="Содержание пользовательской заметки",
        examples=["iPhone 15 Pro в цвете Natural Titanium"],
    )


class CreateNoteRequest(UpdateNoteRequest):
    """Схема запроса на создание пользовательской заметки.

    Используется в качестве представления информации о новой заметке.
    Наследуется от `UpdateNoteRequest`, т.к. имеет
    те же поля, но расширяет набор данных.

    Attributes
    ----------
    type : NoteType
        Тип пользовательской заметки.
    title : str
        Заголовок пользовательской заметки.
    content : str
        Содержание пользовательской заметки.
    """

    type: NoteType = Field(
        description="Тип пользовательской заметки",
        examples=[NoteType.WISHLIST],
    )
