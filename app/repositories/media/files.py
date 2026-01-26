from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import FileStatus
from app.models.file import FileModel
from app.repositories.interface import RepositoryInterface
from app.schemas.dto.file import FileDTO


class FilesRepository(RepositoryInterface):
    """Репозиторий медиа-файлов.

    Реализация паттерна Репозиторий для работы с медиа-файлами.
    Отвечает за CRUD операции с файлами и управление их статусами.

    Methods
    -------
    add_file(object_key, content_type, created_by, title=None, description=None, geo_data=None)
        Добавляет в базу данных новую запись о загруженном медиа файле.
    add_pending_file(object_key, content_type, created_by, title=None, description=None, geo_data=None)
        Добавляет в базу данных новую запись о загружаемом медиа файле.
    get_files_by_ids(files_ids, user_id, partner_id)
        Получает медиа-файлы по списку UUID.
    mark_file_uploaded(file_id)
        Обновляет статус файла на UPLOADED после успешной загрузки.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    def add_file(
        self,
        object_key: str,
        content_type: str,
        created_by: UUID,
        file_id: UUID | None = None,
        title: str | None = None,
        description: str | None = None,
        geo_data: dict[str, Any] | None = None,
    ) -> None:
        """Добавляет в базу данных новую запись о загруженном медиа файле.

        Добавляет запись со статусом файла `FileStatus.UPLOADED`.

        Parameters
        ----------
        object_key : str
            Путь до файла внутри бакета приложения.
        content_type : str
            Content Type переданного файла.
        created_by : UUID
            UUID пользователя, создавшего файл.
        file_id : UUID | None
            UUID медиа-файла.
        title : str | None
            Наименование файла.
        description : str | None
            Описание файла.
        geo_data : dict[str, Any] | None
            Географические данные файла.
        """
        if file_id is None:
            file_id = uuid4()

        self.session.add(
            FileModel(
                id=file_id,
                object_key=object_key,
                content_type=content_type,
                status=FileStatus.UPLOADED,
                title=title,
                description=description,
                geo_data=geo_data,
                created_by=created_by,
            )
        )

    def add_pending_file(
        self,
        object_key: str,
        content_type: str,
        created_by: UUID,
        file_id: UUID | None = None,
        title: str | None = None,
        description: str | None = None,
        geo_data: dict[str, Any] | None = None,
    ) -> UUID:
        """Добавляет в базу данных новую запись о загружаемом медиа файле.

        Добавляет запись со статусом файла `FileStatus.PENDING`.

        Parameters
        ----------
        object_key : str
            Путь до файла внутри бакета приложения.
        content_type : str
            Content Type переданного файла.
        created_by : UUID
            UUID пользователя, создавшего файл.
        file_id : UUID | None
            UUID медиа-файла.
        title : str | None
            Наименование файла.
        description : str | None
            Описание файла.
        geo_data : dict[str, Any] | None
            Географические данные файла.

        Returns
        -------
        UUID
            UUID записи медиа-файла.
        """
        if file_id is None:
            file_id = uuid4()

        self.session.add(
            FileModel(
                id=file_id,
                object_key=object_key,
                content_type=content_type,
                status=FileStatus.PENDING,
                title=title,
                description=description,
                geo_data=geo_data,
                created_by=created_by,
            )
        )

        return file_id

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

        query = (
            select(FileModel)
            .options(selectinload(FileModel.creator))
            .where(FileModel.id.in_(files_ids))
            .order_by(FileModel.created_at)
        )

        if partner_id:
            query = query.where(FileModel.created_by.in_([user_id, partner_id]))
        else:
            query = query.where(FileModel.created_by == user_id)

        files = await self.session.scalars(query)

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

    async def delete_file_by_id(self, file_id: UUID) -> None:
        """Удаляет запись о медиа файле из базы данных по его UUID.

        Parameters
        ----------
        file_id : UUID
            UUID файла для удаления.
        """
        await self.session.execute(delete(FileModel).where(FileModel.id == file_id))
