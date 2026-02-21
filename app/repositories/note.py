import asyncio
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import NoteType, SortOrder
from app.models.note import NoteModel
from app.repositories.interface import SharedResourceRepository
from app.schemas.dto.note import NoteDTO


class NoteRepository(SharedResourceRepository):
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
    count_notes_by_creator(user_id, partner_id)
        Возвращает количество заметок по id их создателя.
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
        note = await self.session.scalar(
            select(NoteModel)
            .options(selectinload(NoteModel.creator))
            .where(
                NoteModel.id == note_id,
                self._build_shared_clause(NoteModel, user_id, partner_id),
            )
        )

        return NoteDTO.model_validate(note) if note else None

    async def get_notes_by_creator(
        self,
        note_type: NoteType | None,
        offset: int,
        limit: int,
        user_id: UUID,
        order: SortOrder,
        partner_id: UUID | None = None,
    ) -> tuple[list[NoteDTO], int]:
        """Возвращает список DTO пользовательских заметок по id их создателя.

        Parameters
        ----------
        note_type : NoteType | None
            Тип заметок для получения.
        offset : int
            Смещение от начала списка.
        limit : int
            Количество возвращаемых заметок.
        order : SortOrder
            Направление сортировки заметок.
        user_id : UUID
            UUID текущего пользователя.
        partner_id : UUID | None, optional
            UUID партнёра текущего пользователя.

        Returns
        -------
        tuple[list[NoteDTO], int]
            Кортеж из списка DTO заметок и общего количества.
        """
        query = (
            select(NoteModel)
            .options(selectinload(NoteModel.creator))
            .slice(offset, offset + limit)
        )

        query = query.order_by(self._build_order_clause(NoteModel.created_at, order))

        where_clauses = [self._build_shared_clause(NoteModel, user_id, partner_id)]
        if note_type:
            where_clauses.append(NoteModel.type == note_type)

        query = query.where(*where_clauses)
        count_query = self._build_count_query(NoteModel, *where_clauses)

        notes, total = await asyncio.gather(
            self.session.scalars(query),
            self.session.scalar(count_query),
        )

        return [NoteDTO.model_validate(note) for note in notes.all()], total or 0

    async def count_notes_by_creator(
        self,
        user_id: UUID,
        partner_id: UUID | None = None,
    ) -> int:
        """Возвращает количество заметок по id их создателя.

        Parameters
        ----------
        user_id : UUID
            UUID текущего пользователя.
        partner_id : UUID | None, optional
            UUID партнёра текущего пользователя.

        Returns
        -------
        int
            Количество доступных пользователю заметок.
        """
        where_clause = self._build_shared_clause(NoteModel, user_id, partner_id)
        count_query = self._build_count_query(NoteModel, where_clause)

        return await self.session.scalar(count_query) or 0

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
