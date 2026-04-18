import asyncio
from uuid import UUID

from sqlalchemy import delete, insert, select, update
from sqlalchemy.orm import selectinload

from app.core.enums import NoteType, SortOrder
from app.infra.postgres.tables import notes_table, users_table
from app.repositories.interface import AccessContext, OwnedRepositoryInterface
from app.schemas.dto.note import CreateNoteDTO, NoteDTO, UpdateNoteDTO


class NoteRepository(OwnedRepositoryInterface[CreateNoteDTO, UpdateNoteDTO, NoteDTO]):
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

    async def create(self, create_dto: CreateNoteDTO, created_by: UUID) -> NoteDTO:
        result = await self.connection.execute(
            insert(notes_table)
            .values(
                **create_dto.to_create_values(),
                created_by=created_by,
            )
            .returning(notes_table)
        )
        row = result.mappings().one()

        return NoteDTO.model_validate(row)

    async def get_by_id(
        self, record_id: UUID, access_ctx: AccessContext
    ) -> NoteDTO | None:
        """Возвращает DTO пользовательской заметки по её id.

        Parameters
        ----------
        record_id : UUID
            UUID пользовательской заметки.
        access_ctx : AccessContext
            Контекст ограниченного доступа к записи.

        Returns
        -------
        NoteDTO | None
            DTO записи заметки или None, если заметка не найдена.
        """
        result = await self.connection.execute(
            select(notes_table, *self._creator_columns())
            .join(users_table, notes_table.c.created_by == users_table.c.id)
            .where(
                notes_table.c.id == record_id,
                access_ctx.as_where_clause(notes_table.c.created_by),
            )
        )
        row = result.mappings().first()

        if row is None:
            return None

        return NoteDTO.model_validate({**row, "creator": self._extract_creator(row)})

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

    async def update_note_by_id(
        self,
        note_id: UUID,
        patch_note_dto: UpdateNoteDTO,
        user_id: UUID,
        partner_id: UUID | None = None,
    ) -> bool:
        """Обновление атрибутов заметки в базе данных.

        Выполняет SQL-запрос UPDATE для изменения атрибутов заметки,
        фильтруя записи по идентификатору заметки и правам доступа
        через `_build_shared_clause`.

        Parameters
        ----------
        note_id : UUID
            UUID заметки к изменению.
        patch_note_dto : UpdateNoteDTO
            DTO с полями для обновления. Только явно переданные поля
            попадают в SET-часть запроса через `to_update_values()`.
        user_id : UUID
            UUID текущего пользователя.
        partner_id : UUID | None, optional
            UUID партнёра текущего пользователя. Передаётся в
            `_build_shared_clause` для проверки прав на заметки партнёра.

        Returns
        -------
        bool
            True, если запись была обновлена, False - если заметка
            не найдена или не прошла проверку прав доступа.
        """
        updated = await self.session.scalar(
            update(NoteModel)
            .where(
                NoteModel.id == note_id,
                self._build_shared_clause(NoteModel, user_id, partner_id),
            )
            .values(**patch_note_dto.to_update_values())
            .returning(NoteModel.id)
        )

        return updated is not None

    async def delete_note_by_id(self, note_id: UUID) -> None:
        """Удаляет запись о пользовательской заметке из базы данных по её UUID.

        Parameters
        ----------
        note_id : UUID
            UUID заметки для удаления.
        """
        await self.session.execute(delete(NoteModel).where(NoteModel.id == note_id))
