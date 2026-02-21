import asyncio
from uuid import UUID

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import FileStatus, SortOrder
from app.models.file import FileModel
from app.repositories.interface import SharedResourceRepository
from app.schemas.dto.file import FileDTO, FileMetadataDTO


class FileRepository(SharedResourceRepository):
    """Репозиторий медиа-файлов.

    Реализация паттерна Репозиторий для работы с медиа-файлами.
    Отвечает за CRUD операции с файлами и управление их статусами.

    Methods
    -------
    add_pending_files(files_metadata, object_keys, created_by)
        Добавляет в базу данных новые записи о загружаемых медиа-файлах.
    get_files_by_creator(offset, limit, user_id, partner_id)
        Получение списка файлов по создателю.
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
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session)

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
                        **m.model_dump(),
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
        title: str | None,
        description: str | None,
    ) -> None:
        """Обновление атрибутов файла в базе данных.

        Выполняет SQL-запрос UPDATE для изменения атрибутов файла,
        фильтруя записи по идентификатору файла и правам создателя.

        Parameters
        ----------
        album_id : UUID
            UUID файла к изменению.
        title : str
            Новое значение заголовка файла.
        description : str | None
            Новое значение описания файла.
        """
        await self.session.execute(
            update(FileModel)
            .where(FileModel.id == file_id)
            .values(
                title=title,
                description=description,
            )
        )

    async def delete_file_by_id(self, file_id: UUID) -> None:
        """Удаляет запись о медиа файле из базы данных по его UUID.

        Parameters
        ----------
        file_id : UUID
            UUID файла для удаления.
        """
        await self.session.execute(delete(FileModel).where(FileModel.id == file_id))
