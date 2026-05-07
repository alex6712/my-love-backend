import asyncio
from typing import Any, Sequence

from sqlalchemy import ColumnElement, Select, delete, insert, select, update

from app.core.consts import DEFAULT_LIMIT, DEFAULT_OFFSET
from app.core.enums import SortOrder
from app.infra.postgres.tables.notes import notes_table
from app.infra.postgres.tables.users import users_table
from app.repositories.interface import (
    USER_PROJECTION_FIELDS,
    AccessContext,
    Counter,
    Creator,
    Deleter,
    Reader,
    Updater,
)
from app.schemas.dto.note import (
    CreateNoteDTO,
    FilterManyNotesDTO,
    FilterOneNoteDTO,
    NoteDTO,
    UpdateNoteDTO,
)


class NoteRepository(
    Creator[CreateNoteDTO],
    Reader[FilterOneNoteDTO, FilterManyNotesDTO, NoteDTO],
    Updater[FilterOneNoteDTO, FilterManyNotesDTO, UpdateNoteDTO],
    Deleter[FilterOneNoteDTO, FilterManyNotesDTO],
    Counter[FilterManyNotesDTO],
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
    create_one(create_dto)
        Создаёт новую заметку с привязкой к владельцу.
    read_one(filter_dto, access_ctx)
        Возвращает DTO пользовательской заметки.
    read_one_for_update(filter_dto, access_ctx)
        Возвращает заметку с блокировкой строки для последующего изменения.
    read_many(filter_dto, access_ctx, offset, limit, sort_order)
        Возвращает отфильтрованный постраничный список заметок и их общее количество.
    update_one(filter_dto, update_dto, access_ctx)
        Обновление атрибутов заметки в базе данных.
    delete_one(filter_dto, access_ctx)
        Удаляет запись о пользовательской заметке из базы данных.
    count(filter_dto, access_ctx)
        Возвращает количество заметок по фильтру и контексту доступа.
    """

    async def create_one(self, create_dto: CreateNoteDTO) -> bool:
        """Создаёт новую заметку с привязкой к владельцу.

        Parameters
        ----------
        create_dto : CreateNoteDTO
            Данные для создания заметки.

        Returns
        -------
        bool
            True если заметка успешно создана.
        """
        result = await self.connection.execute(
            insert(notes_table).values(**create_dto.to_create_values())
        )

        return result.rowcount == 1

    async def create_many(self, create_dtos: Sequence[CreateNoteDTO]) -> int:
        """Не поддерживается для данной сущности.

        Не предусмотрено создание множества заметок за одну транзакцию,
        т.к. такой пользовательский сценарий не существует.
        """
        raise NotImplementedError(
            "Method 'create_many' is not implemented in NoteRepository"
        )

    @classmethod
    def _build_read_statement(cls, *where_clauses: ColumnElement[bool]) -> Select[Any]:
        """Строит SELECT-запрос для чтения заметки.

        Принимает готовые WHERE-условия и выполняет JOIN `users_table`
        для получения DTO создателя.

        Используется в `read_one`, `read_one_for_update` и `read_many`
        во избежание дублирования логики построения запроса.

        Parameters
        ----------
        where_clauses : list[ColumnElement[bool]]
            Выражения для передачи в WHERE-часть запроса.

        Returns
        -------
        Select[Any]
            Готовый SELECT-запрос без исполнения.
        """
        return (
            select(
                notes_table,
                *cls._label_columns(users_table, USER_PROJECTION_FIELDS, "creator"),
            )
            .join(users_table, users_table.c.id == notes_table.c.creator_id)
            .where(*where_clauses)
        )

    async def read_one(
        self, filter_dto: FilterOneNoteDTO, access_ctx: AccessContext
    ) -> NoteDTO | None:
        """Возвращает DTO пользовательской заметки.

        Parameters
        ----------
        filter_dto : FilterOneNoteDTO
            DTO с полями фильтрации.
        access_ctx : AccessContext
            Контекст доступа.

        Returns
        -------
        NoteDTO | None
            DTO записи заметки или None, если заметка не найдена.
        """
        result = await self.connection.execute(
            self._build_read_statement(
                *self._build_filter_clauses(filter_dto, notes_table),
                access_ctx.as_where_clause(notes_table),
            )
        )

        if not (row := result.mappings().first()):
            return None

        return NoteDTO.model_validate(
            {
                **row,
                "creator": self._extract_prefixed(
                    row, "creator", USER_PROJECTION_FIELDS
                ),
            }
        )

    async def read_one_for_update(
        self, filter_dto: FilterOneNoteDTO, access_ctx: AccessContext
    ) -> NoteDTO | None:
        """Возвращает заметку с блокировкой строки для последующего изменения.

        Делегирует построение запроса в `_build_read_statement`.
        Устанавливает `SELECT ... FOR UPDATE` - строка блокируется
        до завершения транзакции. Должен вызываться внутри транзакции.

        Parameters
        ----------
        filter_dto : FilterOneNoteDTO
            DTO с полями фильтрации.
        access_ctx : AccessContext
            Контекст доступа.

        Returns
        -------
        NoteDTO | None
            Найденная заметка с вложенным DTO создателя или None,
            если ни одна заметка не соответствует фильтрам.
        """
        result = await self.connection.execute(
            self._build_read_statement(
                *self._build_filter_clauses(filter_dto, notes_table),
                access_ctx.as_where_clause(notes_table),
            ).with_for_update()
        )

        if not (row := result.mappings().first()):
            return None

        return NoteDTO.model_validate(
            {
                **row,
                "creator": self._extract_prefixed(
                    row, "creator", USER_PROJECTION_FIELDS
                ),
            }
        )

    async def read_many(
        self,
        filter_dto: FilterManyNotesDTO,
        access_ctx: AccessContext,
        *,
        offset: int = DEFAULT_OFFSET,
        limit: int = DEFAULT_LIMIT,
        sort_order: SortOrder = SortOrder.DESC,
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
            Контекст доступа.
        offset : int, optional
            Количество пропускаемых записей, по умолчанию `DEFAULT_OFFSET`.
        limit : int, optional
            Максимальное количество возвращаемых записей, по умолчанию `DEFAULT_LIMIT`.
        sort_order : SortOrder, optional
            Направление сортировки по полю `created_at`,
            по умолчанию `SortOrder.DESC`.

        Returns
        -------
        tuple[list[NoteDTO], int]
            Список DTO найденных заметок и общее количество записей,
            соответствующих фильтрам. Пустой список и 0,
            если заметок нет или доступ ко всем из них запрещён.
        """
        where_clauses = [
            *self._build_filter_clauses(filter_dto, notes_table),
            access_ctx.as_where_clause(notes_table),
        ]

        result, total = await asyncio.gather(
            self.connection.execute(
                self._build_read_statement(*where_clauses)
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
                NoteDTO.model_validate(
                    {
                        **row,
                        "creator": self._extract_prefixed(
                            row, "creator", USER_PROJECTION_FIELDS
                        ),
                    }
                )
                for row in result.mappings().all()
            ],
            total or 0,
        )

    async def update_one(
        self,
        filter_dto: FilterOneNoteDTO,
        update_dto: UpdateNoteDTO,
        access_ctx: AccessContext,
    ) -> bool:
        """Обновление атрибутов заметки в базе данных.

        Выполняет SQL-запрос UPDATE для изменения атрибутов заметки,
        фильтруя записи по переданному DTO и правам доступа
        через `access_ctx.as_where_clause`.

        Parameters
        ----------
        filter_dto : FilterOneNoteDTO
            Параметры фильтрации.
        update_dto : UpdateNoteDTO
            DTO с полями для обновления.
        access_ctx : AccessContext
            Контекст доступа.

        Returns
        -------
        bool
            True если заметка найдена и успешно обновлёна.
        """
        result = await self.connection.execute(
            update(notes_table)
            .values(**update_dto.to_update_values())
            .where(
                *self._build_filter_clauses(filter_dto, notes_table),
                access_ctx.as_where_clause(notes_table),
            )
        )

        return result.rowcount == 1

    async def update_many(
        self,
        filter_dto: FilterManyNotesDTO,
        update_dto: UpdateNoteDTO,
        access_ctx: AccessContext,
    ) -> int:
        """Не поддерживается для данной сущности.

        Не предусмотрено обновление множества заметок за одну транзакцию,
        т.к. такой пользовательский сценарий не существует..
        """
        raise NotImplementedError(
            "Method 'update_many' is not implemented in NoteRepository"
        )

    async def delete_one(
        self, filter_dto: FilterOneNoteDTO, access_ctx: AccessContext
    ) -> bool:
        """Удаляет запись о пользовательской заметке из базы данных.

        Parameters
        ----------
        filter_dto : FilterOneNoteDTO
            Параметры фильтрации.
        access_ctx : AccessContext
            Контекст доступа.

        NoteDTO
        -------
        bool
            True если заметка найдена и успешно удалена.
        """
        result = await self.connection.execute(
            delete(notes_table).where(
                *self._build_filter_clauses(filter_dto, notes_table),
                access_ctx.as_where_clause(notes_table),
            )
        )

        return result.rowcount == 1

    async def delete_many(
        self, filter_dto: FilterManyNotesDTO, access_ctx: AccessContext
    ) -> int:
        """Не поддерживается для данной сущности.

        Не предусмотрено удаление множества заметок за одну транзакцию,
        т.к. такой пользовательский сценарий не существует.
        """
        raise NotImplementedError(
            "Method 'delete_many' is not implemented in NoteRepository"
        )

    async def count(
        self, filter_dto: FilterManyNotesDTO, access_ctx: AccessContext
    ) -> int:
        """Возвращает количество заметок по фильтру и контексту доступа.

        Parameters
        ----------
        filter_dto : FilterManyNotesDTO
            Параметры фильтрации. Пустой DTO инициирует подсчёт
            всей таблицы.
        access_ctx : AccessContext
            Контекст доступа.

        Returns
        -------
        int
            Количество заметок, удовлетворяющих параметрам фильтрации
            и контексту доступа.
        """
        return (
            await self.connection.scalar(
                self._build_count_query(
                    notes_table,
                    *self._build_filter_clauses(filter_dto, notes_table),
                    access_ctx.as_where_clause(notes_table),
                )
            )
            or 0
        )
