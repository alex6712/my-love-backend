import asyncio
from typing import Sequence
from uuid import UUID

from sqlalchemy import delete, insert, select, update

from app.core.consts import DEFAULT_LIMIT, DEFAULT_OFFSET
from app.core.enums import FileStatus, SortOrder
from app.infra.postgres.tables.files import files_table
from app.infra.postgres.tables.users import users_table
from app.repositories.interface import (
    AccessContext,
    OwnedBatchCreateMixin,
    OwnedBatchDeleteMixin,
    OwnedBatchReadMixin,
    OwnedCreateMixin,
    OwnedDeleteMixin,
    OwnedReadMixin,
    OwnedRepositoryInterface,
    OwnedUpdateMixin,
)
from app.schemas.dto.file import (
    CreateFileDTO,
    FileDTO,
    UpdateFileDTO,
)


class FileRepository(
    OwnedRepositoryInterface,
    OwnedCreateMixin[CreateFileDTO, FileDTO],
    OwnedBatchCreateMixin[CreateFileDTO, FileDTO],
    OwnedReadMixin[FileDTO],
    OwnedBatchReadMixin[FileDTO],
    OwnedUpdateMixin[UpdateFileDTO, FileDTO],
    OwnedDeleteMixin[FileDTO],
    OwnedBatchDeleteMixin[FileDTO],
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
    get_by_id(record_id, access_ctx)
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

    async def create(self, create_dto: CreateFileDTO, created_by: UUID) -> FileDTO:
        """Добавляет в базу данных запись о загружаемом медиа-файле.

        Изначально запись о файле имеет статус `FileStatus.PENDING` и
        ожидает подтверждения окончания загрузки файла.

        Parameters
        ----------
        create_dto : CreateFileDTO
            Данные для создания записи о медиа-файле.
        created_by : UUID
            Идентификатор пользователя, загружающего файл.
            Передаётся явно, так как извлекается из payload токена,
            а не из схемы запроса.

        Returns
        -------
        FileDTO
            Доменное DTO созданной записи о файле.
        """
        insert_cte = (
            insert(files_table)
            .values(
                **create_dto.to_create_values(),
                status=FileStatus.PENDING,
                created_by=created_by,
            )
            .returning(files_table)
            .cte("insert_cte")
        )
        result = await self.connection.execute(
            select(insert_cte, *self._creator_columns()).join(
                users_table, insert_cte.c.created_by == users_table.c.id
            )
        )
        row = result.mappings().one()

        return FileDTO.model_validate({**row, "creator": self._extract_creator(row)})

    async def create_batch(
        self, create_dtos: Sequence[CreateFileDTO], created_by: UUID
    ) -> list[FileDTO]:
        """Добавляет в базу данных записи о загружаемых медиа-файлах.

        Изначально все записи имеют статус `FileStatus.PENDING` и
        ожидают подтверждения окончания загрузки файлов.

        Parameters
        ----------
        create_dtos : Sequence[CreateFileDTO]
            Данные для создания записей о медиа-файлах.
        created_by : UUID
            Идентификатор пользователя, загружающего файлы.
            Передаётся явно, так как извлекается из payload токена,
            а не из схемы запроса.

        Returns
        -------
        list[FileDTO]
            Список доменных DTO созданных записей о файлах.
            Порядок соответствует порядку create_dtos.
        """
        insert_cte = (
            insert(files_table)
            .values(
                [
                    {
                        **dto.to_create_values(),
                        "status": FileStatus.PENDING,
                        "created_by": created_by,
                    }
                    for dto in create_dtos
                ]
            )
            .returning(files_table)
            .cte("insert_cte")
        )
        result = await self.connection.execute(
            select(insert_cte, *self._creator_columns()).join(
                users_table, insert_cte.c.created_by == users_table.c.id
            )
        )
        rows = result.mappings().all()

        return [
            FileDTO.model_validate({**row, "creator": self._extract_creator(row)})
            for row in rows
        ]

    async def count(self, access_ctx: AccessContext) -> int:
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
                    files_table, access_ctx.as_where_clause(files_table.c.created_by)
                )
            )
            or 0
        )

    async def get_all(
        self,
        access_ctx: AccessContext,
        *,
        offset: int = DEFAULT_OFFSET,
        limit: int = DEFAULT_LIMIT,
        sort_order: SortOrder = SortOrder.ASC,
    ) -> tuple[list[FileDTO], int]:
        """Возвращает постраничный список медиа-файлов и их общее количество.

        Условие доступа и фильтры применяются на уровне запроса атомарно.
        Общее количество возвращается без учёта пагинации - для формирования
        метаданных ответа на клиенте.

        Parameters
        ----------
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
        tuple[list[FileDTO], int]
            Список DTO найденных файлов и общее количество записей.
            Пустой список и 0, если файлов нет или доступ ко всем из них запрещён.
        """
        where_clause = access_ctx.as_where_clause(files_table.c.created_by)

        result, total = await asyncio.gather(
            self.connection.execute(
                select(files_table, *self._creator_columns())
                .join(users_table, files_table.c.created_by == users_table.c.id)
                .where(where_clause)
                .order_by(
                    self._build_order_clause(files_table.c.created_at, sort_order)
                )
                .slice(offset, offset + limit)
            ),
            self.connection.scalar(self._build_count_query(files_table, where_clause)),
        )

        return (
            [
                FileDTO.model_validate({**row, "creator": self._extract_creator(row)})
                for row in result.mappings().all()
            ],
            total or 0,
        )

    async def get_by_id(
        self, record_id: UUID, access_ctx: AccessContext
    ) -> FileDTO | None:
        """Получает медиа-файл по его UUID.

        Возвращает DTO медиа-файла с указанным UUID
        и создателем (текущей пользователь или его партнёр).

        Parameters
        ----------
        record_id : UUID
            UUID пользовательского медиа-файла.
        access_ctx : AccessContext
            Контекст доступа с идентификаторами владельца и партнёра.

        Returns
        -------
        NoteDTO | None
            Доменное DTO записи медиа-файла или None, если файл не найден.
        """
        result = await self.connection.execute(
            select(files_table, *self._creator_columns())
            .join(users_table, files_table.c.created_by == users_table.c.id)
            .where(
                files_table.c.id == record_id,
                access_ctx.as_where_clause(files_table.c.created_by),
            )
        )

        if not (row := result.mappings().first()):
            return None

        return FileDTO.model_validate({**row, "creator": self._extract_creator(row)})

    async def get_by_ids(
        self, record_ids: Sequence[UUID], access_ctx: AccessContext
    ) -> list[FileDTO]:
        """Получает медиа-файлы по списку UUID.

        Возвращает DTO медиа-файлов, доступных в рамках контекста доступа.
        Недоступные и несуществующие записи молча исключаются из результата.

        Parameters
        ----------
        record_ids : Sequence[UUID]
            UUID запрашиваемых медиа-файлов.
        access_ctx : AccessContext
            Контекст доступа с идентификаторами владельца и партнёра.

        Returns
        -------
        list[FileDTO]
            Список DTO медиа-файлов, доступных в рамках контекста.
            Порядок не гарантирован. Размер списка может быть меньше
            len(record_ids), если часть файлов недоступна или не существует.
        """
        result = await self.connection.execute(
            select(files_table, *self._creator_columns())
            .join(users_table, files_table.c.created_by == users_table.c.id)
            .where(
                files_table.c.id.in_(record_ids),
                access_ctx.as_where_clause(files_table.c.created_by),
            )
        )

        return [
            FileDTO.model_validate({**row, "creator": self._extract_creator(row)})
            for row in result.mappings().all()
        ]

    async def update(
        self,
        record_id: UUID,
        update_dto: UpdateFileDTO,
        access_ctx: AccessContext,
    ) -> FileDTO | None:
        """Обновление атрибутов файла в базе данных.

        Выполняет SQL-запрос UPDATE для изменения атрибутов файла,
        фильтруя записи по идентификатору файла и правам доступа.

        Parameters
        ----------
        record_id : UUID
            UUID файла к изменению.
        update_dto : UpdateFileDTO
            DTO с полями для обновления. Только явно переданные поля
            попадают в SET-часть запроса через `to_update_values()`.
        access_ctx : AccessContext
            Контекст доступа с идентификаторами владельца и партнёра.

        Returns
        -------
        FileDTO | None
            Доменное DTO файла, если он обновлён, None - в ином случае.
        """
        update_cte = (
            update(files_table)
            .where(
                files_table.c.id == record_id,
                access_ctx.as_where_clause(files_table.c.created_by),
            )
            .values(**update_dto.to_update_values())
            .returning(files_table)
            .cte("update_cte")
        )
        result = await self.connection.execute(
            select(update_cte, *self._creator_columns()).join(
                users_table, update_cte.c.created_by == users_table.c.id
            )
        )

        if not (row := result.mappings().first()):
            return None

        return FileDTO.model_validate({**row, "creator": self._extract_creator(row)})

    async def delete(
        self, record_id: UUID, access_ctx: AccessContext
    ) -> FileDTO | None:
        """Удаляет запись о медиа файле из базы данных по его UUID.

        Parameters
        ----------
        record_id : UUID
            UUID файла для удаления.
        access_ctx : AccessContext
            Контекст доступа с идентификаторами владельца и партнёра.

        Returns
        -------
        FileDTO | None
            Доменное DTO файла, если он удалён, None - в ином случае.
        """
        delete_cte = (
            delete(files_table)
            .where(
                files_table.c.id == record_id,
                access_ctx.as_where_clause(files_table.c.created_by),
            )
            .returning(files_table)
            .cte("delete_cte")
        )
        result = await self.connection.execute(
            select(delete_cte, *self._creator_columns()).join(
                users_table, delete_cte.c.created_by == users_table.c.id
            )
        )

        if not (row := result.mappings().first()):
            return None

        return FileDTO.model_validate({**row, "creator": self._extract_creator(row)})

    async def delete_batch(
        self, record_ids: Sequence[UUID], access_ctx: AccessContext
    ) -> list[FileDTO]:
        """Удаляет записи о медиа-файлах из базы данных по списку UUID.

        Parameters
        ----------
        record_ids : Sequence[UUID]
            UUID файлов для удаления.
        access_ctx : AccessContext
            Контекст доступа с идентификаторами владельца и партнёра.

        Returns
        -------
        list[FileDTO]
            Список DTO удалённых медиа-файлов.
            Пустой список, если записей нет или доступ ко всем из них запрещён.
        """
        delete_cte = (
            delete(files_table)
            .where(
                files_table.c.id.in_(record_ids),
                access_ctx.as_where_clause(files_table.c.created_by),
            )
            .returning(files_table)
            .cte("delete_cte")
        )
        result = await self.connection.execute(
            select(delete_cte, *self._creator_columns()).join(
                users_table, delete_cte.c.created_by == users_table.c.id
            )
        )

        return [
            FileDTO.model_validate({**row, "creator": self._extract_creator(row)})
            for row in result.mappings().all()
        ]
