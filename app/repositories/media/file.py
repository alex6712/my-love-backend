import asyncio
from uuid import UUID

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import FileStatus, SortOrder
from app.models.file import FileModel
from app.repositories.interface import SharedResourceRepository
from app.schemas.dto.file import (
    FileDTO,
    FileMetadataDTO,
    InternalFileMetadataDTO,
    PatchFileDTO,
)


class FileRepository(SharedResourceRepository):
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

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def add_pending_file(
        self, file_metadata: FileMetadataDTO, object_key: str, created_by: UUID
    ) -> UUID:
        """Добавляет в базу данных запись о загружаемом медиа-файле.

        Запись создаётся со статусом ``FileStatus.PENDING``.

        Parameters
        ----------
        file_metadata : FileMetadataDTO
            DTO с метаданными файла.
        object_key : str
            Ключ объекта в S3 (путь к файлу в хранилище).
        created_by : UUID
            UUID пользователя, создающего запись.

        Returns
        -------
        UUID
            UUID созданной записи медиа-файла.

        Raises
        ------
        RuntimeError
            Если INSERT не вернул идентификатор созданной записи.
        """
        metadata = InternalFileMetadataDTO.model_validate(
            file_metadata.model_dump(exclude={"client_ref_id"})
        )

        file_id = await self.session.scalar(
            insert(FileModel)
            .values(
                {
                    "object_key": object_key,
                    "status": FileStatus.PENDING,
                    "created_by": created_by,
                    **metadata.model_dump(),
                }
            )
            .returning(FileModel.id)
        )

        if not file_id:
            raise RuntimeError(
                "Unknown error is occurred while trying to create new file entry."
            )

        return file_id

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

    async def get_files_by_creator(
        self,
        offset: int,
        limit: int,
        order: SortOrder,
        user_id: UUID,
        partner_id: UUID | None = None,
    ) -> tuple[list[FileDTO], int]:
        """Возвращает список DTO медиа файлов по id их создателя.

        Parameters
        ----------
        offset : int
            Смещение от начала списка.
        limit : int
            Количество возвращаемых файлов.
        order : SortOrder
            Направление сортировки файлов.
        user_id : UUID
            UUID текущего пользователя.
        partner_id : UUID | None, optional
            UUID партнёра текущего пользователя.

        Returns
        -------
        tuple[list[FileDTO], int]
            Кортеж из списка DTO файлов и общего количества.
        """
        query = (
            select(FileModel)
            .options(selectinload(FileModel.creator))
            .slice(offset, offset + limit)
        )

        query = query.order_by(self._build_order_clause(FileModel.created_at, order))

        where_clause = self._build_shared_clause(FileModel, user_id, partner_id)

        query = query.where(where_clause)
        count_query = self._build_count_query(FileModel, where_clause)

        files, total = await asyncio.gather(
            self.session.scalars(query),
            self.session.scalar(count_query),
        )

        return [FileDTO.model_validate(file) for file in files.all()], total or 0

    async def count_files_by_creator(
        self,
        user_id: UUID,
        partner_id: UUID | None = None,
    ) -> int:
        """Возвращает количество медиа-файлов по id их создателя.

        Parameters
        ----------
        user_id : UUID
            UUID текущего пользователя.
        partner_id : UUID | None, optional
            UUID партнёра текущего пользователя.

        Returns
        -------
        int
            Количество доступных пользователю медиа-файлов.
        """
        where_clause = self._build_shared_clause(FileModel, user_id, partner_id)
        count_query = self._build_count_query(FileModel, where_clause)

        return await self.session.scalar(count_query) or 0

    async def get_file_by_id(
        self,
        file_id: UUID,
        user_id: UUID,
        partner_id: UUID | None = None,
    ) -> FileDTO | None:
        """Получает медиа-файл по его UUID.

        Возвращает DTO медиа-файла с указанным UUID
        и создателем (текущей пользователь или его партнёр).

        Parameters
        ----------
        file_id : UUID
            UUID медиа-файла.
        user_id : UUID | None
            UUID пользователя, чей файл ищется.
        partner_id : UUID | None, optional
            Если указано, ищет также среди файлов партнёра.

        Returns
        -------
        FileDTO
            DTO найденного медиа-файла.
        """
        files = await self.get_files_by_ids([file_id], user_id, partner_id)

        return files[0] if len(files) == 1 else None

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

    async def mark_file_uploaded(self, file_id: UUID) -> None:
        """Обновляет статус файла на UPLOADED после успешной загрузки.

        Parameters
        ----------
        file_id : UUID
            Уникальный идентификатор файла.
        """
        await self.session.execute(
            update(FileModel)
            .where(FileModel.id == file_id)
            .values(status=FileStatus.UPLOADED)
        )

    async def update_file_by_id(
        self,
        file_id: UUID,
        patch_file_dto: PatchFileDTO,
        user_id: UUID,
    ) -> bool:
        """Обновление атрибутов файла в базе данных.

        Выполняет SQL-запрос UPDATE для изменения атрибутов файла,
        фильтруя записи по идентификатору файла и правам доступа.

        Parameters
        ----------
        file_id : UUID
            UUID файла к изменению.
        patch_file_dto : PatchFileDTO
            DTO с полями для обновления. Только явно переданные поля
            попадают в SET-часть запроса через `to_update_values()`.
        user_id : UUID
            UUID текущего пользователя.

        Returns
        -------
        bool
            True, если запись была обновлена, False - если файл
            не найден или не прошёл проверку прав доступа.
        """
        updated = await self.session.scalar(
            update(FileModel)
            .where(
                FileModel.id == file_id,
                FileModel.created_by == user_id,
            )
            .values(**patch_file_dto.to_update_values())
            .returning(FileModel.id)
        )

        return updated is not None

    async def delete_file_by_id(self, file_id: UUID) -> None:
        """Удаляет запись о медиа файле из базы данных по его UUID.

        Parameters
        ----------
        file_id : UUID
            UUID файла для удаления.
        """
        await self.session.execute(delete(FileModel).where(FileModel.id == file_id))

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
