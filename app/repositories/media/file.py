from typing import Any, Sequence

from sqlalchemy import ColumnElement, Select, delete, insert, select, update

from app.core.consts import DEFAULT_LIMIT, DEFAULT_OFFSET
from app.core.enums import SortOrder
from app.infra.postgres.tables.files import files_table
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
from app.schemas.dto.file import (
    CreateFileDTO,
    FileDTO,
    FilterManyFilesDTO,
    FilterOneFileDTO,
    UpdateFileDTO,
)


class FileRepository(
    Creator[CreateFileDTO],
    Reader[FilterOneFileDTO, FilterManyFilesDTO, FileDTO],
    Updater[FilterOneFileDTO, FilterManyFilesDTO, UpdateFileDTO],
    Deleter[FilterOneFileDTO, FilterManyFilesDTO],
    Counter[FilterManyFilesDTO],
):
    """Репозиторий медиа-файлов.

    Реализация паттерна Репозиторий для работы с медиа-файлами.
    Отвечает за CRUD операции с файлами и управление их статусами.

    Methods
    -------
    create(create_dto, created_by)
        Создаёт запись о медиа-файле со статусом `FileStatus.PENDING`.
    create_batch(create_dtos, created_by)
        Массово создаёт записи о медиа-файлах со статусом `FileStatus.PENDING`.
    count(access_ctx)
        Возвращает количество медиа-файлов, доступных в рамках контекста доступа.
    get_all(access_ctx, offset, limit, sort_order)
        Возвращает постраничный список медиа-файлов и их общее количество.
    get_one(record_id, access_ctx)
        Получает медиа-файл по его UUID с учётом прав доступа.
    get_by_ids(record_ids, access_ctx)
        Получает список медиа-файлов по UUID с учётом прав доступа.
    update(record_id, update_dto, access_ctx)
        Обновляет атрибуты медиа-файла по его UUID.
    delete(record_id, access_ctx)
        Удаляет медиа-файл по его UUID.
    delete_batch(record_ids, access_ctx)
        Массово удаляет медиа-файлы по списку UUID.
    """

    async def create_one(self, create_dto: CreateFileDTO) -> bool:
        """Создаёт новую запись о медиа-файле с привязкой к владельцу.

        Parameters
        ----------
        create_dto : CreateNoteDTO
            Данные для создания записи медиа-файла.

        Returns
        -------
        bool
            True если запись медиа-файла успешно создана.
        """
        result = await self.connection.execute(
            insert(files_table).values(**create_dto.to_create_values())
        )

        return result.rowcount == 1

    async def create_many(self, create_dtos: Sequence[CreateFileDTO]) -> int:
        """Создает множество записей медиа-файлов с привязкой к владельцу.

        Parameters
        ----------
        create_dtos : Sequence[CreateFileDTO]
            Данные для создания записей медиа-файлов.

        Returns
        -------
        int
            Количество успешно созданных записей.
        """
        result = await self.connection.execute(
            insert(files_table).values(
                [{**dto.to_create_values()} for dto in create_dtos]
            )
        )

        return result.rowcount

    @classmethod
    def _build_read_statement(cls, *where_clauses: ColumnElement[bool]) -> Select[Any]:
        """Строит SELECT-запрос для чтения записи о медиа-файле.

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
                files_table,
                *cls._label_columns(users_table, USER_PROJECTION_FIELDS, "creator"),
            )
            .join(users_table, users_table.c.id == files_table.c.created_by)
            .where(*where_clauses)
        )

    async def read_one(
        self, filter_dto: FilterOneFileDTO, access_ctx: AccessContext
    ) -> FileDTO | None:
        """Возвращает DTO пользовательского медиа-файла.

        Parameters
        ----------
        filter_dto : FilterOneFileDTO
            DTO с полями фильтрации.
        access_ctx : AccessContext
            Контекст доступа.

        Returns
        -------
        FileDTO | None
            DTO записи медиа-файла или None, если запись не найдена.
        """
        result = await self.connection.execute(
            self._build_read_statement(
                *self._build_filter_clauses(filter_dto, files_table),
                access_ctx.as_where_clause(files_table),
            )
        )

        if not (row := result.mappings().first()):
            return None

        return FileDTO.model_validate(
            {
                **row,
                "creator": self._extract_prefixed(
                    row, "creator", USER_PROJECTION_FIELDS
                ),
            }
        )

    async def read_one_for_update(
        self, filter_dto: FilterOneFileDTO, access_ctx: AccessContext
    ) -> FileDTO | None:
        """Возвращает DTO пользовательского медиа-файла с блокировкой строки для последующего изменения.

        Делегирует построение запроса в `_build_read_statement`.
        Устанавливает `SELECT ... FOR UPDATE` - строка блокируется
        до завершения транзакции. Должен вызываться внутри транзакции.

        Parameters
        ----------
        filter_dto : FilterOneFileDTO
            DTO с полями фильтрации.
        access_ctx : AccessContext
            Контекст доступа.

        Returns
        -------
        NoteDTO | None
            Найденная запись о медиа-файле с вложенным DTO создателя
            или None, если ни одна запись не соответствует фильтрам.
        """
        result = await self.connection.execute(
            self._build_read_statement(
                *self._build_filter_clauses(filter_dto, files_table),
                access_ctx.as_where_clause(files_table),
            ).with_for_update()
        )

        if not (row := result.mappings().first()):
            return None

        return FileDTO.model_validate(
            {
                **row,
                "creator": self._extract_prefixed(
                    row, "creator", USER_PROJECTION_FIELDS
                ),
            }
        )

    async def read_many(
        self,
        filter_dto: FilterManyFilesDTO,
        access_ctx: AccessContext,
        *,
        offset: int = DEFAULT_OFFSET,
        limit: int = DEFAULT_LIMIT,
        sort_order: SortOrder = SortOrder.DESC,
    ) -> list[FileDTO]:
        """Возвращает отфильтрованный постраничный список медиа-файлов.

        Условие доступа и фильтры применяются на уровне запроса атомарно.

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
        list[NoteDTO]
            Список DTO найденных записей медиа-файлов, удовлетворяющих фильтру.
        """
        where_clauses = [
            *self._build_filter_clauses(filter_dto, files_table),
            access_ctx.as_where_clause(files_table),
        ]

        result = await self.connection.execute(
            self._build_read_statement(*where_clauses)
            .order_by(self._build_order_clause(files_table.c.created_at, sort_order))
            .slice(offset, offset + limit)
        )

        return [
            FileDTO.model_validate(
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
        filter_dto: FilterOneFileDTO,
        update_dto: UpdateFileDTO,
        access_ctx: AccessContext,
    ) -> bool:
        """Обновление атрибутов файла в базе данных.

        Выполняет SQL-запрос UPDATE для изменения атрибутов файла,
        фильтруя записи по идентификатору файла и правам доступа.

        Parameters
        ----------
        filter_dto : FilterOneFileDTO
            Параметры фильтрации.
        update_dto : UpdateNoteDTO
            DTO с полями для обновления.
        access_ctx : AccessContext
            Контекст доступа.

        Returns
        -------
        bool
            True если запись о медиа-файле найдена и успешно обновлёна.
        """
        result = await self.connection.execute(
            update(files_table)
            .values(**update_dto.to_update_values())
            .where(
                *self._build_filter_clauses(filter_dto, files_table),
                access_ctx.as_where_clause(files_table),
            )
        )

        return result.rowcount == 1

    async def update_many(
        self,
        filter_dto: FilterManyFilesDTO,
        update_dto: UpdateFileDTO,
        access_ctx: AccessContext,
    ) -> int:
        """Не поддерживается для данной сущности.

        Не предусмотрено обновление множества медиа-файлов за одну транзакцию,
        т.к. такой пользовательский сценарий не существует.
        """
        raise NotImplementedError(
            "Method 'update_many' is not implemented in FileREpository"
        )

    async def delete_one(
        self, filter_dto: FilterOneFileDTO, access_ctx: AccessContext
    ) -> bool:
        """Удаляет запись о медиа-файле из базы данных.

        Parameters
        ----------
        filter_dto : FilterOneFileDTO
            Параметры фильтрации.
        access_ctx : AccessContext
            Контекст доступа.

        NoteDTO
        -------
        bool
            True если запись о медиа-файле найдена и успешно удалена.
        """
        result = await self.connection.execute(
            delete(files_table).where(
                *self._build_filter_clauses(filter_dto, files_table),
                access_ctx.as_where_clause(files_table),
            )
        )

        return result.rowcount == 1

    async def delete_many(
        self, filter_dto: FilterManyFilesDTO, access_ctx: AccessContext
    ) -> int:
        """Удаляет множество записей о медиа-файлов из базы данных.

        Parameters
        ----------
        filter_dto : FilterManyFilesDTO
            Параметры фильтрации.
        access_ctx : AccessContext
            Контекст доступа.

        Returns
        -------
        int
            Количество успешно удалённых записей.
        """
        result = await self.connection.execute(
            delete(files_table).where(
                *self._build_filter_clauses(filter_dto, files_table),
                access_ctx.as_where_clause(files_table),
            )
        )

        return result.rowcount

    async def count(
        self, filter_dto: FilterManyFilesDTO, access_ctx: AccessContext
    ) -> int:
        """Возвращает количество медиа-файлов по id их создателя.

        Parameters
        ----------
        access_ctx : AccessContext
            Контекст доступа с идентификаторами владельца и партнёра.

        Returns
        -------
        int
            Количество доступных пользователю медиа-файлов.
        """
        return (
            await self.connection.scalar(
                self._build_count_query(
                    files_table,
                    *self._build_filter_clauses(filter_dto, files_table),
                    access_ctx.as_where_clause(files_table),
                )
            )
            or 0
        )
