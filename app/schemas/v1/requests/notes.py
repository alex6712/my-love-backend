from pydantic import BaseModel, Field

from app.core.enums import NoteType
from app.core.types import UNSET, Maybe


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


class PatchNoteRequest(BaseModel):
    """Схема запроса на частичное редактирование заметки.

    Используется в качестве представления данных для частичного
    обновления полей пользовательской заметки. Все поля опциональны -
    передаются только те атрибуты, которые необходимо изменить.

    Attributes
    ----------
    title : Maybe[str]
        Заголовок пользовательской заметки. Если не передан - остаётся `UNSET`
        и текущее значение в базе данных не изменяется.
    content : Maybe[str]
        Содержание пользовательской заметки. Если не передан - остаётся `UNSET`
        и текущее значение в базе данных не изменяется.
    """

    title: Maybe[str] = Field(
        default_factory=lambda: UNSET,
        description="Заголовок пользовательской заметки",
        examples=["Новый телефон"],
    )
    content: Maybe[str] = Field(
        default_factory=lambda: UNSET,
        description="Содержание пользовательской заметки",
        examples=["iPhone 15 Pro в цвете Natural Titanium"],
    )
