from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import NoteType
from app.models.note import NoteModel
from app.repositories.interface import RepositoryInterface


class NotesRepository(RepositoryInterface):
    """Репозиторий пользовательских заметок.

    Реализация паттерна Репозиторий. Является объектом доступа к данным (DAO).
    Реализует основные CRUD операции с пользовательскими заметками.

    Attributes
    ----------
    session : AsyncSession
        Объект асинхронной сессии запроса.

    Methods
    -------
    add_note(type, title, content, created_by)
        Создание новой пользовательской заметки.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    def add_note(
        self,
        type: NoteType,
        title: str,
        content: str,
        created_by: UUID,
    ) -> None:
        """Создание новой пользовательской заметки.

        Добавляет в базу данных запись о новой пользовательской заметке
        и устанавливает переданные атрибуты.

        Parameters
        ----------
        type : NoteType
            Тип пользовательской заметки.
        title : str
            Заголовок пользовательской заметки.
        content : str
            Содержимое пользовательской заметки
        created_by : UUID
            UUID пользователя, загрузившего заметку.
        """
        self.session.add(
            NoteModel(
                type=type,
                title=title,
                content=content,
                created_by=created_by,
            )
        )
