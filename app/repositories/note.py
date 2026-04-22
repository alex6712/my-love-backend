import asyncio
from uuid import UUID

from sqlalchemy import delete, insert, select, update

from app.core.consts import DEFAULT_LIMIT, DEFAULT_OFFSET
from app.core.enums import SortOrder
from app.infra.postgres.tables.notes import notes_table
from app.infra.postgres.tables.users import users_table
from app.repositories.interface import (
    AccessContext,
    OwnedCreateMixin,
    OwnedDeleteMixin,
    OwnedFilteredReadMixin,
    OwnedRepositoryInterface,
    OwnedUpdateMixin,
)
from app.schemas.dto.note import CreateNoteDTO, FilterNoteDTO, NoteDTO, UpdateNoteDTO


class NoteRepository(
    OwnedRepositoryInterface,
    OwnedFilteredReadMixin[FilterNoteDTO, NoteDTO],
    OwnedCreateMixin[CreateNoteDTO, NoteDTO],
    OwnedUpdateMixin[UpdateNoteDTO, NoteDTO],
    OwnedDeleteMixin[NoteDTO],
):
    """Репозиторий пользовательских заметок.

    Реализация паттерна Репозиторий. Является объектом доступа к данным (DAO).
    Реализует основные CRUD операции с пользовательскими заметками.

    Attributes
    ----------
    session : AsyncSession
        Объект асинхронной сессии запроса.

    Methods
    -------
    create(create_dto, created_by)
        Создаёт новую заметку с привязкой к владельцу.
    get_all(access_ctx, offset, limit, sort_order)
        Возвращает постраничный список записей, доступных в рамках контекста.
    get_by_id(record_id, access_ctx)
        Возвращает DTO пользовательской заметки по её id.
    count(access_ctx)
        Возвращает количество заметок по id их создателя.
    update(record_id, update_dto, access_ctx)
        Обновление атрибутов заметки в базе данных.
    delete(record_id, access_ctx)
        Удаляет запись о пользовательской заметке из базы данных по её UUID.
    """

    async def create(self, create_dto: CreateNoteDTO, created_by: UUID) -> NoteDTO:
        """Создаёт новую заметку с привязкой к владельцу.

        Parameters
        ----------
        create_dto : CreateNoteDTO
            Данные для создания заметки.
        created_by : UUID
            Идентификатор пользователя, создающего заметку.
            Передаётся явно, так как извлекается из payload токена,
            а не из схемы запроса.

        Returns
        -------
        NoteDTO
            Доменное DTO созданной заметки.
        """
        insert_cte = (
            insert(notes_table)
            .values(**create_dto.to_create_values(), created_by=created_by)
            .returning(notes_table)
            .cte("insert_cte")
        )
        result = await self.connection.execute(
            select(insert_cte, *self._creator_columns()).join(
                users_table, insert_cte.c.created_by == users_table.c.id
            )
        )
        row = result.mappings().one()

        return NoteDTO.model_validate({**row, "creator": self._extract_creator(row)})

    async def get_filtered(
        self,
        filter_dto: FilterNoteDTO,
        access_ctx: AccessContext,
        *,
        offset: int = DEFAULT_OFFSET,
        limit: int = DEFAULT_LIMIT,
        sort_order: SortOrder = SortOrder.ASC,
    ) -> tuple[list[NoteDTO], int]:
        """Возвращает отфильтрованный постраничный список заметок и их общее количество.

        Условие доступа и фильтры применяются на уровне запроса атомарно.
        Общее количество возвращается без учёта пагинации - для формирования
        метаданных ответа на клиенте.

        Parameters
        ----------
        filter_dto : FilterNoteDTO
            Параметры фильтрации. Пустой DTO возвращает все записи.
        access_ctx : AccessContext
            Контекст доступа с идентификаторами владельца и партнёра.
        offset : int, optional
            Количество пропускаемых записей, по умолчанию `DEFAULT_OFFSET`.
        limit : int, optional
            Максимальное количество возвращаемых записей, по умолчанию `DEFAULT_LIMIT`.
        sort_order : SortOrder, optional
            Направление сортировки по полю `created_at`,
            по умолчанию SortOrder.ASC.

        Returns
        -------
        tuple[list[NoteDTO], int]
            Список DTO найденных заметок и общее количество записей,
            соответствующих фильтрам. Пустой список и 0,
            если заметок нет или доступ ко всем из них запрещён.
        """
        where_clauses = [
            getattr(notes_table.c, field) == value
            for field, value in filter_dto.to_filter_values().items()
        ]
        where_clauses.append(access_ctx.as_where_clause(notes_table.c.created_by))

        result, total = await asyncio.gather(
            self.connection.execute(
                select(notes_table, *self._creator_columns())
                .join(users_table, notes_table.c.created_by == users_table.c.id)
                .where(*where_clauses)
                .order_by(
                    self._build_order_clause(notes_table.c.created_at, sort_order)
                )
                .slice(offset, offset + limit)
            ),
            self.connection.scalar(
                self._build_count_query(notes_table, *where_clauses)
            ),
        )

        return (
            [
                NoteDTO.model_validate({**row, "creator": self._extract_creator(row)})
                for row in result.mappings().all()
            ],
            total or 0,
        )

    async def get_by_id(
        self, record_id: UUID, access_ctx: AccessContext
    ) -> NoteDTO | None:
        """Возвращает DTO пользовательской заметки по её id.

        Parameters
        ----------
        record_id : UUID
            UUID пользовательской заметки.
        access_ctx : AccessContext
            Контекст доступа с идентификаторами владельца и партнёра.

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

        if not (row := result.mappings().first()):
            return None

        return NoteDTO.model_validate({**row, "creator": self._extract_creator(row)})

    async def count(self, access_ctx: AccessContext) -> int:
        """Возвращает количество заметок по id их создателя.

        Parameters
        ----------
        access_ctx : AccessContext
            Контекст доступа с идентификаторами владельца и партнёра.

        Returns
        -------
        int
            Количество доступных пользователю заметок.
        """
        return (
            await self.connection.scalar(
                self._build_count_query(
                    notes_table, access_ctx.as_where_clause(notes_table.c.created_by)
                )
            )
            or 0
        )

    async def update(
        self, record_id: UUID, update_dto: UpdateNoteDTO, access_ctx: AccessContext
    ) -> NoteDTO | None:
        """Обновление атрибутов заметки в базе данных.

        Выполняет SQL-запрос UPDATE для изменения атрибутов заметки,
        фильтруя записи по идентификатору заметки и правам доступа
        через `access_ctx.as_where_clause`.

        Parameters
        ----------
        note_id : UUID
            UUID заметки к изменению.
        patch_note_dto : UpdateNoteDTO
            DTO с полями для обновления. Только явно переданные поля
            попадают в SET-часть запроса через `to_update_values()`.
        access_ctx : AccessContext
            Контекст доступа с идентификаторами владельца и партнёра.

        Returns
        -------
        NoteDTO | None
            Доменное DTO заметки, если она обновлена, None - в ином
            случае.
        """
        update_cte = (
            update(notes_table)
            .where(
                notes_table.c.id == record_id,
                access_ctx.as_where_clause(notes_table.c.created_by),
            )
            .values(**update_dto.to_update_values())
            .returning(notes_table)
            .cte("update_cte")
        )
        result = await self.connection.execute(
            select(update_cte, *self._creator_columns()).join(
                users_table, update_cte.c.created_by == users_table.c.id
            )
        )

        if not (row := result.mappings().first()):
            return None

        return NoteDTO.model_validate({**row, "creator": self._extract_creator(row)})

    async def delete(
        self, record_id: UUID, access_ctx: AccessContext
    ) -> NoteDTO | None:
        """Удаляет запись о пользовательской заметке из базы данных по её UUID.

        Parameters
        ----------
        note_id : UUID
            UUID заметки для удаления.
        access_ctx : AccessContext
            Контекст доступа с идентификаторами владельца и партнёра.

        NoteDTO
        -------
        FileDTO | None
            Доменное DTO заметки, если она удалёна, None - в ином
            случае.
        """
        delete_cte = (
            delete(notes_table)
            .where(
                notes_table.c.id == record_id,
                access_ctx.as_where_clause(notes_table.c.created_by),
            )
            .returning(notes_table)
            .cte("delete_cte")
        )
        result = await self.connection.execute(
            select(delete_cte, *self._creator_columns()).join(
                users_table, delete_cte.c.created_by == users_table.c.id
            )
        )

        if not (row := result.mappings().first()):
            return None

        return NoteDTO.model_validate({**row, "creator": self._extract_creator(row)})
