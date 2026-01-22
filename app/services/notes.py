from typing import TYPE_CHECKING
from uuid import UUID

from app.core.enums import NoteType
from app.infrastructure.postgresql import UnitOfWork
from app.repositories.notes import NotesRepository

if TYPE_CHECKING:
    pass


class NotesService:
    """Сервис работы с пользовательскими заметками.

    Реализует бизнес-логику для:
    - менеджмента пользовательских заметок.

    Attributes
    ----------
    _notes_repo : NotesRepository
        Репозиторий для операций с заметками в БД.

    Methods
    -------
    """

    def __init__(self, unit_of_work: UnitOfWork):
        super().__init__()

        self._notes_repo: NotesRepository = unit_of_work.get_repository(NotesRepository)

    def create_note(
        self, type: NoteType, title: str, content: str, created_by: UUID
    ) -> None:
        self._notes_repo.add_note(type, title, content, created_by)
