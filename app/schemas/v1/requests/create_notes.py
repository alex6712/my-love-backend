from pydantic import BaseModel, Field

from app.core.enums import NoteType


class CreateNoteRequest(BaseModel):
    """Схема запроса на создание пользовательской заметки.

    Используется в качестве представления информации о новой заметке.

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
    title: str = Field(
        default="Новая заметка",
        description="Заголовок пользовательской заметки",
        examples=["Новый телефон"],
    )
    content: str = Field(
        description="Содержание пользовательской заметки",
        examples=["iPhone 15 Pro в цвете Natural Titanium"],
    )
