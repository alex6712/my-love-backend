import asyncio
from uuid import UUID

from sqlalchemy import delete, insert, select, update
from sqlalchemy.orm import selectinload

from app.core.consts import DEFAULT_LIMIT, DEFAULT_OFFSET
from app.core.enums import FileStatus, SortOrder
from app.infra.postgres.tables.files import files_table
from app.infra.postgres.tables.users import users_table
from app.models.file import FileModel
from app.repositories.interface import (
    AccessContext,
    OwnedCreateMixin,
    OwnedDeleteMixin,
    OwnedReadMixin,
    OwnedRepositoryInterface,
    OwnedUpdateMixin,
)
from app.schemas.dto.file import (
    CreateFileDTO,
    FileDTO,
    FileMetadataDTO,
    InternalFileMetadataDTO,
    UpdateFileDTO,
)


class FileRepository(
    OwnedRepositoryInterface,
    OwnedReadMixin[FileDTO],
    OwnedCreateMixin[CreateFileDTO, FileDTO],
    OwnedUpdateMixin[UpdateFileDTO, FileDTO],
    OwnedDeleteMixin,
):
    """Репозиторий медиа-файлов.

    Реализация паттерна Репозиторий для работы с медиа-файлами.
    Отвечает за CRUD операции с файлами и управление их статусами.

    Methods
    -------
    add_pending_file(file_metadata, object_key, created_by)
        Добавляет в базу данных запись о загружаемом медиа-файле.
    add_pending_files(files_metadata, object_keys, created_by)
        Добавляет в базу данных новые записи о загружаемых медиа-файлах.
    get_files_by_creator(offset, limit, user_id, partner_id)
        Получение списка файлов по создателю.
    count_files_by_creator(user_id, partner_id)
        Возвращает количество медиа-файлов по id их создателя.
    get_file_by_id(file_id, user_id, partner_id)
        Получает медиа-файл по его UUID.
    get_files_by_ids(files_ids, user_id, partner_id)
        Получает медиа-файлы по списку UUID.
    mark_file_uploaded(file_id)
        Обновляет статус файла на UPLOADED после успешной загрузки.
    update_file_by_id(file_id, title, description)
        Обновление атрибутов файла в базе данных.
    delete_file_by_id(file_id):
        Удаляет запись о медиа файле из базы данных по его UUID.
    delete_pending_files_by_ids(file_ids)
        Удаляет записи медиа-файлов со статусом `FileStatus.PENDING` по их идентификаторам.
    """

    async def create(self, create_dto: CreateFileDTO, created_by: UUID) -> FileDTO:
        """Добавляет в базу данных запись о загружаемом медиа-файле.

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
            .values(**create_dto.to_create_values(), created_by=created_by)
            .returning(files_table)
            .cte("insert_cte")
        )
        result = await self.connection.execute(
            select(files_table, *self._creator_columns()).join(
                users_table, insert_cte.c.created_by == users_table.c.id
            )
        )
        row = result.mappings().one()

        return FileDTO.model_validate({**row, "creator": self._extract_creator(row)})

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

    async def add_pending_files(
        self,
        files_metadata: list[FileMetadataDTO],
        object_keys: list[str],
        created_by: UUID,
    ) -> list[UUID]:
        """Добавляет в базу данных новые записи о загружаемых медиа-файлах.

        Все записи добавляются со статусом `FileStatus.PENDING`.

        Parameters
        ----------
        files_metadata : list[FileMetadataDTO]
            Список DTO и метаинформацией файлов.
        object_keys : list[str]
            Список ключей объектов (= идентификаторов файлов в S3).
        created_by : UUID
            UUID пользователя, создавшего файл.

        Returns
        -------
        list[UUID]
            UUID записей медиа-файлов.
        """
        file_ids = await self.session.scalars(
            insert(FileModel)
            .values(
                [
                    {
                        "object_key": k,
                        "status": FileStatus.PENDING,
                        "created_by": created_by,
                        **InternalFileMetadataDTO.model_validate(
                            m.model_dump(exclude={"client_ref_id"})
                        ).model_dump(),
                    }
                    for m, k in zip(files_metadata, object_keys, strict=True)
                ]
            )
            .returning(FileModel.id)
        )

        return list(file_ids)

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

        data_query = (
            select(files_table, *self._creator_columns())
            .join(users_table, files_table.c.created_by == users_table.c.id)
            .where(where_clause)
            .order_by(self._build_order_clause(files_table.c.created_at, sort_order))
            .slice(offset, offset + limit)
        )

        data_result, total = await asyncio.gather(
            self.connection.execute(data_query),
            self.connection.scalar(self._build_count_query(files_table, where_clause)),
        )

        return (
            [
                FileDTO.model_validate({**row, "creator": self._extract_creator(row)})
                for row in data_result.mappings().all()
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

    async def get_files_by_ids(
        self,
        files_ids: list[UUID],
        user_id: UUID,
        partner_id: UUID | None = None,
    ) -> list[FileDTO]:
        """Получает медиа-файлы по списку UUID.

        Возвращает список DTO медиа-файлов с указанными UUID
        и создателем (текущей пользователь и его партнёр).

        Parameters
        ----------
        files_ids : list[UUID]
            Список UUID медиа-файлов.
        user_id : UUID | None
            UUID пользователя, чьи файлы ищутся.
        partner_id : UUID | None, optional
            Если указано, ищут также файла партнёра.

        Returns
        -------
        list[FileDTO]
            Список найденных медиа-файлов.
        """
        if not files_ids:
            return []

        files = await self.session.scalars(
            select(FileModel)
            .options(selectinload(FileModel.creator))
            .where(
                FileModel.id.in_(files_ids),
                self._build_shared_clause(FileModel, user_id, partner_id),
            )
            .order_by(FileModel.created_at)
        )

        return [FileDTO.model_validate(file) for file in files.all()]

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
            Доменное DTO файла, если он обновлён, None - в ином
            случае.
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

    async def delete(self, record_id: UUID, access_ctx: AccessContext) -> bool:
        """Удаляет запись о медиа файле из базы данных по его UUID.

        Parameters
        ----------
        record_id : UUID
            UUID файла для удаления.
        access_ctx : AccessContext
            Контекст доступа с идентификаторами владельца и партнёра.

        Returns
        -------
        bool
            True если запись о файле удалена, False если файл по переданному
            `record_id` не найден или пользователь не имеет достаточно прав.
        """
        result = await self.connection.execute(
            delete(FileModel).where(
                files_table.c.id == record_id,
                access_ctx.as_where_clause(files_table.c.created_by),
            )
        )

        return result.mappings().first() is not None

    async def delete_pending_files_by_ids(self, file_ids: list[UUID]) -> None:
        """Удаляет записи медиа-файлов со статусом `FileStatus.PENDING` по их идентификаторам.

        Записи с любым другим статусом не затрагиваются,
        даже если их идентификаторы присутствуют в списке.

        Parameters
        ----------
        file_ids : list[UUID]
            Список UUID записей для удаления.
        """
        await self.session.execute(
            delete(FileModel).where(
                FileModel.id.in_(file_ids), FileModel.status == FileStatus.PENDING
            )
        )
