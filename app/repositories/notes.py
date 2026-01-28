from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import NoteType
from app.models.note import NoteModel
from app.repositories.interface import RepositoryInterface
from app.schemas.dto.note import NoteDTO


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
    get_note_by_id(note_id, user_id, partner_id)
        Возвращает DTO пользовательской заметки по её id.
    get_notes_by_creator(offset, limit, user_id, partner_id)
        Возвращает список DTO пользовательских заметок по id их создателя.
    update_note_by_id(note_id, title, content)
        Обновление атрибутов заметки в базе данных.
    delete_note_by_id(note_id)
        Удаляет запись о пользовательской заметке из базы данных по её UUID.
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

    async def get_note_by_id(
        self, note_id: UUID, user_id: UUID, partner_id: UUID | None = None
    ) -> NoteDTO | None:
        """Возвращает DTO пользовательской заметки по её id.

        Parameters
        ----------
        note_id : UUID
            UUID пользовательской заметки.
        user_id : UUID
            UUID текущего пользователя.
        partner_id : UUID | None, optional
            UUID партнёра текущего пользователя.

        Returns
        -------
        NoteDTO | None
            DTO записи заметки или None, если заметка не найден.
        """
        query = (
            select(NoteModel)
            .options(selectinload(NoteModel.creator))
            .where(NoteModel.id == note_id)
        )

        if partner_id:
            query = query.where(NoteModel.created_by.in_([user_id, partner_id]))
        else:
            query = query.where(NoteModel.created_by == user_id)

        note = await self.session.scalar(query)

        return NoteDTO.model_validate(note) if note else None

    async def get_notes_by_creator(
        self, offset: int, limit: int, user_id: UUID, partner_id: UUID | None = None
    ) -> list[NoteDTO]:
        """Возвращает список DTO пользовательских заметок по id их создателя.

        Parameters
        ----------
        offset : int
            Смещение от начала списка.
        limit : int
            Количество возвращаемых заметок.
        user_id : UUID
            UUID текущего пользователя.
        partner_id : UUID | None, optional
            UUID партнёра текущего пользователя.

        Returns
        -------
        list[NoteDTO]
            Список DTO заметок доступных пользователю.
        """
        query = (
            select(NoteModel)
            .options(selectinload(NoteModel.creator))
            .order_by(NoteModel.created_at)
            .slice(offset, offset + limit)
        )

        if partner_id:
            query = query.where(NoteModel.created_by.in_([user_id, partner_id]))
        else:
            query = query.where(NoteModel.created_by == user_id)

        albums = await self.session.scalars(query)

        return [NoteDTO.model_validate(album) for album in albums.all()]

    async def update_note_by_id(self, note_id: UUID, title: str, content: str) -> None:
        """Обновление атрибутов заметки в базе данных.

        Выполняет SQL-запрос UPDATE для изменения атрибутов заметки,
        фильтруя записи по идентификатору заметки и правам создателя.

        Parameters
        ----------
        note_id : UUID
            UUID заметки к изменению.
        title : str
            Новое значение заголовка пользовательской заметки.
        content : str
            Новое значение содержимого пользовательской заметки.
        """
        await self.session.execute(
            update(NoteModel)
            .where(NoteModel.id == note_id)
            .values(title=title, content=content)
        )

    async def delete_note_by_id(self, note_id: UUID) -> None:
        """Удаляет запись о пользовательской заметке из базы данных по её UUID.

        Parameters
        ----------
        note_id : UUID
            UUID заметки для удаления.
        """
        await self.session.execute(delete(NoteModel).where(NoteModel.id == note_id))
