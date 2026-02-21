from uuid import UUID

from app.core.enums import NoteType
from app.core.exceptions.note import NoteNotFoundException
from app.infrastructure.postgresql import UnitOfWork
from app.repositories.couple import CoupleRepository
from app.repositories.note import NoteRepository
from app.schemas.dto.note import NoteDTO


class NoteService:
    """Сервис работы с пользовательскими заметками.

    Реализует бизнес-логику для менеджмента пользовательских заметок.
    Здесь представлены все основные CRUD операции над заметками
    в приложении.

    Attributes
    ----------
    _note_repo : NoteRepository
        Репозиторий для операций с заметками в БД.
    _couple_repo : CoupleRepository
        Репозиторий для операций с парами пользователей в БД.

    Methods
    -------
    create_note(type, title, content, created_by)
        Создание новой пользовательской заметки.
    get_notes(offset, limit, user_id)
        Получение всех заметок по UUID создателя.
    update_note(note_id, title, content, user_id)
        Обновление атрибутов заметки по его UUID.
    delete_note(note_id, user_id)
        Удаление заметки по его UUID.
    """

    def __init__(self, unit_of_work: UnitOfWork):
        super().__init__()

        self._note_repo = unit_of_work.get_repository(NoteRepository)
        self._couple_repo = unit_of_work.get_repository(CoupleRepository)

    def create_note(
        self, type: NoteType, title: str, content: str, created_by: UUID
    ) -> None:
        """Создание новой пользовательской заметки.

        Создаёт новую заметку по переданным данным.

        Parameters
        ----------
        type : NoteType
            Тип пользовательской заметки.
        title : str
            Заголовок пользовательской заметки
        content : str
            Содержимое пользовательской заметки.
        created_by : UUID
            UUID пользователя, создающего заметку.
        """
        self._note_repo.add_note(type, title, content, created_by)

    async def get_notes(
        self, note_type: NoteType | None, offset: int, limit: int, user_id: UUID
    ) -> tuple[list[NoteDTO], int]:
        """Получение всех заметок по UUID создателя.

        Получает на вход UUID пользователя, ищет UUID партнёра,
        возвращает список всех заметок, которые доступны пользователю (
        созданы им или его партнёром).

        Parameters
        ----------
        note_type : NoteType | None
            Тип заметок для получения.
        offset : int
            Смещение от начала списка (количество пропускаемых заметок).
        limit : int
            Количество возвращаемых заметок.
        user_id : UUID
            UUID пользователя.

        Returns
        -------
        tuple[list[NoteDTO], int]
            Кортеж из списка заметок и общего количества.
        """
        partner_id = await self._couple_repo.get_partner_id_by_user_id(user_id)

        return await self._note_repo.get_notes_by_creator(
            note_type, offset, limit, user_id, partner_id
        )

    async def update_note(
        self, note_id: UUID, title: str | None, content: str | None, user_id: UUID
    ) -> None:
        """Частичное обновление атрибутов заметки по его UUID.

        Получает идентификатор партнера текущего пользователя и передает данные
        в репозиторий для обновления заметки с учетом прав доступа.
        Обновляет только те поля, которые переданы (не равны None).

        Parameters
        ----------
        note_id : UUID
            UUID заметки к изменению.
        title : str | None
            Новый заголовок заметки. Если None — текущее значение не изменяется.
        content : str | None
            Новое содержание заметки. Если None — текущее значение не изменяется.
        user_id : UUID
            UUID пользователя, инициирующего изменение заметки.
        """
        partner_id = await self._couple_repo.get_partner_id_by_user_id(user_id)

        note = await self._note_repo.get_note_by_id(note_id, user_id, partner_id)

        if note is None:
            raise NoteNotFoundException(
                detail=f"Note with id={note_id} not found, or you're not this note's creator.",
            )

        if title is None:
            title = note.title
        if content is None:
            content = note.content

        await self._note_repo.update_note_by_id(note_id, title, content)

    async def delete_note(self, note_id: UUID, user_id: UUID) -> None:
        """Удаление заметки по его UUID.

        Получает UUID заметки и UUID пользователя, совершающего действие удаления.
        Если UUID пользователя не совпадает с UUID создателя заметки, завершает
        действие исключением. В ином случае удаляет заметку.

        Parameters
        ----------
        note_id : UUID
            UUID заметки к удалению.
        user_id : UUID
            UUID пользователя, запрашивающего удаление.

        Raises
        ------
        NoteNotFoundException
            Возникает в случае, если заметка с переданным UUID не существует
            или текущий пользователь не является создателем заметки.
        """
        note = await self._note_repo.get_note_by_id(note_id, user_id)

        if note is None:
            raise NoteNotFoundException(
                detail=f"Note with id={note_id} not found, or you're not this note's creator.",
            )

        await self._note_repo.delete_note_by_id(note_id)
