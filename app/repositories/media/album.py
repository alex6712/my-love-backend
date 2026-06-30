import asyncio
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import (
    ColumnElement,
    Select,
    and_,
    case,
    delete,
    exists,
    func,
    insert,
    literal,
    or_,
    select,
    text,
    update,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.consts import DEFAULT_LIMIT, DEFAULT_OFFSET
from app.core.enums import SortOrder
from app.infra.postgres.tables.album_items import album_items_table
from app.infra.postgres.tables.albums import albums_table
from app.infra.postgres.tables.files import files_table
from app.infra.postgres.tables.users import users_table
from app.repositories.interface import (
    USER_PROJECTION_FIELDS,
    AccessContext,
    Counter,
    Creator,
    Deleter,
    Reader,
    Searcher,
    Updater,
)
from app.schemas.dto.album import (
    AlbumDTO,
    CreateAlbumDTO,
    FilterManyAlbumsDTO,
    FilterOneAlbumDTO,
    InternalAlbumWithItemsDTO,
    SearchAlbumDTO,
    UpdateAlbumDTO,
)


class AlbumRepository(
    Creator[CreateAlbumDTO],
    Reader[FilterOneAlbumDTO, FilterManyAlbumsDTO, AlbumDTO],
    Updater[FilterOneAlbumDTO, FilterManyAlbumsDTO, UpdateAlbumDTO],
    Deleter[FilterOneAlbumDTO, FilterManyAlbumsDTO],
    Counter[FilterManyAlbumsDTO],
    Searcher[SearchAlbumDTO, FilterManyAlbumsDTO, AlbumDTO],
):
    """Репозиторий медиаальбомов.

    Реализация паттерна Репозиторий для работы с медиаальбомами.
    Отвечает за CRUD операции с альбомами и управление связями с файлами.

    Methods
    -------
    create(create_dto, created_by)
        Создаёт новый альбом с привязкой к владельцу.
    get_one(record_id, access_ctx)
        Возвращает DTO альбома по его UUID.
    get_all(access_ctx, offset, limit, sort_order)
        Возвращает постраничный список альбомов и их общее количество.
    search_by_trigram(access_ctx, search_query, threshold, offset, limit)
        Производит поиск альбомов по переданному запросу.
    get_with_items(record_id, access_ctx, offset, limit)
        Возвращает DTO альбома с постраничным списком медиафайлов.
    update(record_id, update_dto, access_ctx)
        Обновляет атрибуты альбома в базе данных.
    delete(record_id, access_ctx)
        Удаляет запись о медиаальбоме из базы данных.
    attach_files(record_id, files_ids, access_ctx)
        Прикрепляет медиафайлы к альбому.
    detach_files(record_id, files_ids, access_ctx)
        Открепляет медиафайлы от альбома.
    get_attached_files_ids(album_id, files_ids)
        Возвращает UUID файлов, уже прикреплённых к альбому.
    """

    _LIKE_ESCAPE_CHAR = "\\"
    """Символы экранирования для операции LIKE (и ILIKE)."""

    async def create_one(self, create_dto: CreateAlbumDTO) -> bool:
        """Создаёт новую запись о медиаальбоме с привязкой к владельцу.

        Parameters
        ----------
        create_dto : CreateAlbumDTO
            Данные для создания записи медиаальбома.

        Returns
        -------
        bool
            True если запись медиаальбома успешно создана.
        """
        result = await self.connection.execute(
            insert(albums_table).values(**create_dto.to_create_values())
        )

        return result.rowcount == 1

    async def create_many(self, create_dtos: Sequence[CreateAlbumDTO]) -> int:
        """Не поддерживается для данной сущности.

        Не предусмотрено создание множества медиаальбомов за одну транзакцию,
        т.к. такой пользовательский сценарий не существует.
        """
        raise NotImplementedError(
            "Method 'create_many' is not implemented in AlbumRepository"
        )

    @classmethod
    def _build_read_statement(cls, *where_clauses: ColumnElement[bool]) -> Select[Any]:
        """Строит SELECT-запрос для чтения записи о медиаальбоме.

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
                albums_table,
                *cls._label_columns(users_table, USER_PROJECTION_FIELDS, "creator"),
            )
            .join(users_table, users_table.c.id == albums_table.c.created_by)
            .where(*where_clauses)
        )

    async def read_one(
        self, filter_dto: FilterOneAlbumDTO, access_ctx: AccessContext
    ) -> AlbumDTO | None:
        """Возвращает DTO пользовательского медиаальбома.

        Parameters
        ----------
        filter_dto : FilterOneAlbumDTO
            DTO с полями фильтрации.
        access_ctx : AccessContext
            Контекст доступа.

        Returns
        -------
        AlbumDTO | None
            DTO записи медиаальбома или None, если запись не найдена.
        """
        result = await self.connection.execute(
            self._build_read_statement(
                *self._build_filter_clauses(filter_dto, albums_table),
                access_ctx.as_where_clause(albums_table),
            )
        )

        if not (row := result.mappings().first()):
            return None

        return AlbumDTO.model_validate(
            {
                **row,
                "creator": self._extract_prefixed(
                    row, "creator", USER_PROJECTION_FIELDS
                ),
            }
        )

    async def read_one_for_update(
        self, filter_dto: FilterOneAlbumDTO, access_ctx: AccessContext
    ) -> AlbumDTO | None:
        """Возвращает DTO пользовательского медиаальбома с блокировкой строки для последующего изменения.

        Делегирует построение запроса в `_build_read_statement`.
        Устанавливает `SELECT ... FOR UPDATE` - строка блокируется
        до завершения транзакции. Должен вызываться внутри транзакции.

        Parameters
        ----------
        filter_dto : FilterOneAlbumDTO
            DTO с полями фильтрации.
        access_ctx : AccessContext
            Контекст доступа.

        Returns
        -------
        AlbumDTO | None
            Найденная запись о медиаальбоме с вложенным DTO создателя
            или None, если ни одна запись не соответствует фильтрам.
        """
        result = await self.connection.execute(
            self._build_read_statement(
                *self._build_filter_clauses(filter_dto, albums_table),
                access_ctx.as_where_clause(albums_table),
            )
        )

        if not (row := result.mappings().first()):
            return None

        return AlbumDTO.model_validate(
            {
                **row,
                "creator": self._extract_prefixed(
                    row, "creator", USER_PROJECTION_FIELDS
                ),
            }
        )

    async def read_many(
        self,
        filter_dto: FilterManyAlbumsDTO,
        access_ctx: AccessContext,
        *,
        offset: int = DEFAULT_OFFSET,
        limit: int = DEFAULT_LIMIT,
        sort_order: SortOrder = SortOrder.DESC,
    ) -> list[AlbumDTO]:
        """Возвращает отфильтрованный постраничный список медиаальбомов.

        Условие доступа и фильтры применяются на уровне запроса атомарно.

        Parameters
        ----------
        filter_dto : FilterManyAlbumsDTO
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
        list[AlbumDTO]
            Список DTO найденных записей медиаальбомов, удовлетворяющих фильтру.
        """
        result = await self.connection.execute(
            self._build_read_statement(
                *self._build_filter_clauses(filter_dto, albums_table),
                access_ctx.as_where_clause(albums_table),
            )
            .order_by(self._build_order_clause(albums_table.c.created_at, sort_order))
            .slice(offset, offset + limit)
        )

        return [
            AlbumDTO.model_validate(
                {
                    **row,
                    "creator": self._extract_prefixed(
                        row, "creator", USER_PROJECTION_FIELDS
                    ),
                }
            )
            for row in result.mappings().all()
        ]

    async def update_one(
        self,
        filter_dto: FilterOneAlbumDTO,
        update_dto: UpdateAlbumDTO,
        access_ctx: AccessContext,
    ) -> bool:
        """Обновление атрибутов альбома в базе данных.

        Выполняет SQL-запрос UPDATE для изменения атрибутов альбома,
        фильтруя записи по переданному DTO и правам доступа
        через `access_ctx.as_where_clause`.

        Parameters
        ----------
        filter_dto : FilterOneAlbumDTO
            Параметры фильтрации.
        update_dto : UpdateAlbumDTO
            DTO с полями для обновления.
        access_ctx : AccessContext
            Контекст доступа.

        Returns
        -------
        bool
            True если запись о медиаальбоме найдена и успешно обновлёна.
        """
        result = await self.connection.execute(
            update(albums_table)
            .values(**update_dto.to_update_values())
            .where(
                *self._build_filter_clauses(filter_dto, albums_table),
                access_ctx.as_where_clause(albums_table),
            )
        )

        return result.rowcount == 1

    async def update_many(
        self,
        filter_dto: FilterManyAlbumsDTO,
        update_dto: UpdateAlbumDTO,
        access_ctx: AccessContext,
    ) -> int:
        """Не поддерживается для данной сущности.

        Не предусмотрено обновление множества медиаальбомов за одну транзакцию,
        т.к. такой пользовательский сценарий не существует.
        """
        raise NotImplementedError(
            "Method 'update_many' is not implemented in AlbumRepository"
        )

    async def delete_one(
        self, filter_dto: FilterOneAlbumDTO, access_ctx: AccessContext
    ) -> bool:
        """Удаляет запись о медиаальбоме из базы данных.

        Parameters
        ----------
        filter_dto : FilterOneAlbumDTO
            Параметры фильтрации.
        access_ctx : AccessContext
            Контекст доступа.

        Returns
        -------
        bool
            True если запись о медиаальбоме найдена и успешно удалена.
        """
        result = await self.connection.execute(
            delete(albums_table).where(
                *self._build_filter_clauses(filter_dto, albums_table),
                access_ctx.as_where_clause(albums_table),
            )
        )

        return result.rowcount == 1

    async def delete_many(
        self, filter_dto: FilterManyAlbumsDTO, access_ctx: AccessContext
    ) -> int:
        """Не поддерживается для данной сущности.

        Не предусмотрено удаление множества медиаальбомов за одну транзакцию,
        т.к. такой пользовательский сценарий не существует.
        """
        raise NotImplementedError(
            "Method 'delete_many' is not implemented in AlbumRepository"
        )

    async def count(
        self, filter_dto: FilterManyAlbumsDTO, access_ctx: AccessContext
    ) -> int:
        """Возвращает количество медиаальбомов по фильтру и контексту доступа.

        Parameters
        ----------
        filter_dto : FilterManyAlbumsDTO
            Параметры фильтрации. Пустой DTO инициирует подсчёт
            всей таблицы.
        access_ctx : AccessContext
            Контекст доступа.

        Returns
        -------
        int
            Количество медиаальбомов, удовлетворяющих параметрам фильтрации
            и контексту доступа.
        """
        return (
            await self.connection.scalar(
                self._build_count_query(
                    albums_table,
                    *self._build_filter_clauses(filter_dto, albums_table),
                    access_ctx.as_where_clause(albums_table),
                )
            )
            or 0
        )

    async def search(
        self,
        search_dto: SearchAlbumDTO,
        filter_dto: FilterManyAlbumsDTO,
        access_ctx: AccessContext,
        *,
        offset: int = DEFAULT_OFFSET,
        limit: int = DEFAULT_LIMIT,
    ) -> tuple[list[AlbumDTO], int]:
        """Производит поиск альбомов по переданному запросу.

        Используется гибридный подход с поиском по полному вхождению (ILIKE)
        и по триграммам (% + GIN-индексы). Результат возвращается в порядке
        убывания сходства с запросом:
        - Первыми возвращаются результаты с полным совпадением;
        - Далее следуют результаты, отсортированные по значению функции `similarity`.

        Parameters
        ----------
        search_dto : SearchAlbumDTO
            DTO с данными для поиска.
        filter_dto : FilterManyAlbumsDTO
            Параметры фильтрации.
        access_ctx : AccessContext
            Контекст доступа с идентификаторами владельца и партнёра.
        offset : int, optional
            Количество пропускаемых записей, по умолчанию `DEFAULT_OFFSET`.
        limit : int, optional
            Максимальное количество возвращаемых записей, по умолчанию `DEFAULT_LIMIT`.

        Returns
        -------
        tuple[list[AlbumDTO], int]
            Кортеж из списка найденных альбомов и их общего количества.
        """
        await self.connection.execute(
            text("SELECT set_limit(:threshold)"),
            {"threshold": search_dto.threshold},
        )

        def escape_like(value: str, escape_char: str = self._LIKE_ESCAPE_CHAR) -> str:
            return (
                value.replace(escape_char, escape_char * 2)
                .replace("%", f"{escape_char}%")
                .replace("_", f"{escape_char}_")
            )

        ilike_pattern = f"%{escape_like(search_dto.search_query)}%"

        ilikes = [
            albums_table.c.title.ilike(ilike_pattern, escape=self._LIKE_ESCAPE_CHAR),
            albums_table.c.description.ilike(
                ilike_pattern, escape=self._LIKE_ESCAPE_CHAR
            ),
        ]

        where_clauses = [
            *self._build_filter_clauses(filter_dto, albums_table),
            access_ctx.as_where_clause(albums_table),
            or_(
                # поиск полного вхождения
                *ilikes,
                # поиск по триграммам
                albums_table.c.title.op("%")(search_dto.search_query),
                albums_table.c.description.op("%")(search_dto.search_query),
            ),
        ]

        result, total = await asyncio.gather(
            self.connection.execute(
                self._build_read_statement(*where_clauses)
                .order_by(
                    # полные вхождения в списке идут выше
                    case((or_(*ilikes), 1.0), else_=0.0).desc(),
                    func.greatest(
                        func.coalesce(
                            func.similarity(
                                albums_table.c.title, search_dto.search_query
                            ),
                            0.0,
                        ),
                        func.coalesce(
                            func.similarity(
                                albums_table.c.description, search_dto.search_query
                            ),
                            0.0,
                        ),
                    ).desc(),
                    albums_table.c.created_at,
                )
                .slice(offset, offset + limit)
            ),
            self.connection.scalar(
                self._build_count_query(albums_table, *where_clauses)
            ),
        )

        return [
            AlbumDTO.model_validate(
                {
                    **row,
                    "creator": self._extract_prefixed(
                        row, "creator", USER_PROJECTION_FIELDS
                    ),
                }
            )
            for row in result.mappings().all()
        ], total or 0

    async def get_with_items(
        self,
        filter_dto: FilterOneAlbumDTO,
        access_ctx: AccessContext,
        *,
        offset: int = DEFAULT_OFFSET,
        limit: int = DEFAULT_LIMIT,
    ) -> InternalAlbumWithItemsDTO | None:
        """Получает DTO альбома с постраничным списком медиафайлов.

        Параллельно выполняет три запроса: получение альбома с создателем,
        постраничную выборку медиафайлов и подсчёт их общего количества.
        Файлы фильтруются по тому же контексту доступа, что и альбом.
        Если альбом не найден или недоступен - возвращает None.

        Parameters
        ----------
        filter_dto : FilterOneAlbumDTO
            Параметры фильтрации.
        access_ctx : AccessContext
            Контекст доступа. Применяется как к альбому, так и к его медиафайлам.
        offset : int, optional
            Количество пропускаемых записей, по умолчанию `DEFAULT_OFFSET`.
        limit : int, optional
            Максимальное количество возвращаемых записей, по умолчанию `DEFAULT_LIMIT`.

        Returns
        -------
        InternalAlbumWithItemsDTO | None
            DTO альбома с медиафайлами, или None если альбом не найден.
        """
        album_result, items_result, total = await asyncio.gather(
            # альбом с данными создателя
            self.connection.execute(
                self._build_read_statement(
                    *self._build_filter_clauses(filter_dto, albums_table),
                    access_ctx.as_where_clause(albums_table),
                )
            ),
            # постраничная выборка файлов альбома с данными их создателей
            self.connection.execute(
                select(
                    files_table,
                    *self._label_columns(
                        users_table, USER_PROJECTION_FIELDS, "creator"
                    ),
                )
                .join(users_table, users_table.c.id == files_table.c.created_by)
                .join(
                    album_items_table, album_items_table.c.file_id == files_table.c.id
                )
                .where(
                    items_where_clause := and_(
                        album_items_table.c.album_id == filter_dto.id,
                        access_ctx.as_where_clause(files_table),
                    )
                )
                .slice(offset, offset + limit)
            ),
            # общее количество доступных файлов (без учёта пагинации)
            self.connection.scalar(
                self._build_count_query(
                    album_items_table.join(
                        files_table, files_table.c.id == album_items_table.c.file_id
                    ),
                    items_where_clause,
                )
            ),
        )

        if not (album_row := album_result.mappings().first()):
            return None

        return InternalAlbumWithItemsDTO.model_validate(
            {
                **album_row,
                "creator": self._extract_prefixed(
                    album_row, "creator", USER_PROJECTION_FIELDS
                ),
                "items": [
                    {
                        **item_row,
                        "creator": self._extract_prefixed(
                            item_row, "creator", USER_PROJECTION_FIELDS
                        ),
                    }
                    for item_row in items_result.mappings().all()
                ],
                "total": total or 0,
            }
        )

    async def attach_files(
        self, record_id: UUID, files_ids: list[UUID], access_ctx: AccessContext
    ) -> None:
        """Прикрепляет медиафайлы к альбому.

        Прикрепляет только те файлы, к которым есть доступ по контексту,
        и только если альбом также доступен. Дубликаты молча игнорируются.

        Parameters
        ----------
        record_id : UUID
            UUID альбома.
        files_ids : list[UUID]
            Список UUID медиафайлов для прикрепления.
        access_ctx : AccessContext
            Контекст доступа с идентификаторами владельца и партнёра.
        """
        await self.connection.execute(
            pg_insert(album_items_table)
            .from_select(
                ["album_id", "file_id"],
                select(
                    literal(record_id).label("album_id"),
                    files_table.c.id.label("file_id"),
                ).where(
                    files_table.c.id.in_(files_ids),
                    access_ctx.as_where_clause(files_table),
                    exists(
                        select(albums_table.c.id).where(
                            albums_table.c.id == record_id,
                            access_ctx.as_where_clause(albums_table),
                        )
                    ),
                ),
            )
            .on_conflict_do_nothing(constraint="uq_album_file")
        )

    async def detach_files(
        self, record_id: UUID, files_ids: list[UUID], access_ctx: AccessContext
    ) -> None:
        """Открепляет медиафайлы от альбома.

        Удаление выполняется только если пользователь имеет доступ
        как к самому альбому, так и к каждому из открепляемых файлов.
        Возвращает список UUID файлов, которые были реально удалены,
        что позволяет на уровне сервиса сравнить его с переданным
        списком и сформировать обратную связь для пользователя.

        Parameters
        ----------
        record_id : UUID
            UUID альбома.
        files_ids : list[UUID]
            Список UUID медиафайлов для удаления.
        access_ctx : AccessContext
            Контекст доступа с идентификаторами владельца и партнёра.
        """
        await self.connection.execute(
            delete(album_items_table).where(
                album_items_table.c.album_id == record_id,
                album_items_table.c.file_id.in_(files_ids),
                exists(
                    select(albums_table.c.id).where(
                        albums_table.c.id == record_id,
                        access_ctx.as_where_clause(albums_table),
                    )
                ),
                album_items_table.c.file_id.in_(
                    select(files_table.c.id).where(
                        files_table.c.id.in_(files_ids),
                        access_ctx.as_where_clause(files_table),
                    )
                ),
            )
        )
