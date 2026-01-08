from typing import Any
from uuid import UUID

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.album import AlbumModel
from app.models.album_items import AlbumItemsModel
from app.models.file import FileModel, FileType
from app.repositories.interface import RepositoryInterface
from app.schemas.dto.album import AlbumDTO, AlbumWithItemsDTO
from app.schemas.dto.file import FileDTO


class MediaRepository(RepositoryInterface):
    """Репозиторий медиа альбомов и файлов.

    Реализация паттерна Репозиторий. Является объектом доступа к данным (DAO).
    Реализует основные CRUD операции с различными типами медиа.

    Methods
    -------
    add_file(url, type_, created_by, title=None, description=None, geo_data=None)
        Добавляет в базу данных новую запись о медиа файле.
    add_album(title, description, cover_url, is_private, created_by)
        Добавляет в базу данных новую запись о медиа альбоме.
    get_album_by_id(id_)
        Возвращает DTO медиа альбома по его id.
    get_albums_by_creator_id(creator_id)
        Возвращает список DTO медиа альбомов по id их создателя.
    delete_album_by_id(album_id)
        Удаляет запись о медиа альбоме из базы данных по его id.
    get_files_by_ids(files_ids, created_by)
        Получает медиа-файлы по списку UUID.
    get_existing_album_items(album_id, files_ids)
        Получает UUID медиа-файлов, уже прикреплённых к альбому.
    attach_files_to_album(album_id, files_uuids)
        Прикрепляет медиа-файлы к альбому.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def add_file(
        self,
        object_key: str,
        type_: FileType,
        created_by: UUID,
        title: str | None = None,
        description: str | None = None,
        geo_data: dict[str, Any] | None = None,
    ) -> None:
        """Добавляет в базу данных новую запись о медиа файле.

        Parameters
        ----------
        object_key : str
            Путь до файла внутри бакета приложения.
        type_ : FileType
            Тип файла (например, изображение, видео).
        created_by : UUID
            UUID пользователя, создавшего файл.
        title : str | None
            Наименование файла. По умолчанию `None`.
        description : str | None
            Описание файла. По умолчанию `None`.
        geo_data : dict[str, Any] | None
            Географические данные файла в виде словаря. По умолчанию `None`.
        """
        self.session.add(
            FileModel(
                object_key=object_key,
                type_=type_,
                title=title,
                description=description,
                geo_data=geo_data,
                created_by=created_by,
            )
        )

    async def add_album(
        self,
        title: str,
        description: str | None,
        cover_url: str | None,
        is_private: bool,
        created_by: UUID,
    ) -> None:
        """Добавляет в базу данных новую запись о медиа альбоме.

        Parameters
        ----------
        title : str
            Наименование альбома.
        description : str | None
            Описание альбома.
        cover_url : str | None
            URL обложки альбома.
        is_private : bool
            Видимость альбома:
            - True - личный альбом;
            - False - публичный альбом (значение по умолчанию).
        created_by : UUID
            UUID пользователя, создавшего альбом.
        """
        self.session.add(
            AlbumModel(
                title=title,
                description=description,
                cover_url=cover_url,
                is_private=is_private,
                created_by=created_by,
            )
        )

    async def get_album_by_id(self, album_id: UUID) -> AlbumDTO | None:
        """Возвращает DTO медиа альбома по его id.

        Parameters
        ----------
        album_id : UUID
            UUID альбома.

        Returns
        -------
        AlbumDTO
            DTO записи альбома.
        """
        album: AlbumModel | None = await self.session.scalar(
            select(AlbumModel)
            .options(selectinload(AlbumModel.creator))
            .where(AlbumModel.id == album_id)
        )

        return AlbumDTO.model_validate(album) if album else None

    async def get_album_with_items_by_id(
        self, album_id: UUID
    ) -> AlbumWithItemsDTO | None:
        """Возвращает DTO медиа альбома по его id.

        Parameters
        ----------
        album_id : UUID
            UUID альбома.

        Returns
        -------
        AlbumDTO
            DTO записи альбома.
        """
        album: AlbumModel | None = await self.session.scalar(
            select(AlbumModel)
            .options(
                selectinload(AlbumModel.creator),
                selectinload(AlbumModel.items),
            )
            .where(AlbumModel.id == album_id)
        )

        return AlbumWithItemsDTO.model_validate(album) if album else None

    async def get_albums_by_creator_id(self, creator_id: UUID) -> list[AlbumDTO]:
        """Возвращает список DTO медиа альбомов по id их создателя.

        Parameters
        ----------
        creator_id : UUID
            UUID пользователя, чьи альбомы ищутся.

        Returns
        -------
        list[AlbumDTO]
            Список DTO созданных пользователем альбомов.
        """
        albums = await self.session.scalars(
            select(AlbumModel)
            .options(selectinload(AlbumModel.creator))
            .where(AlbumModel.created_by == creator_id)
        )

        return [AlbumDTO.model_validate(album) for album in albums.all()]

    async def delete_album_by_id(self, album_id: UUID) -> None:
        """Удаляет запись о медиа альбоме из базы данных по его UUID.

        Parameters
        ----------
        album_id : UUID
            UUID альбома для удаления.
        """
        await self.session.execute(delete(AlbumModel).where(AlbumModel.id == album_id))

    async def get_files_by_ids(
        self, files_ids: list[UUID], created_by: UUID | None = None
    ) -> list[FileDTO]:
        """Получает медиа-файлы по списку UUID.

        Parameters
        ----------
        files_ids : list[UUID]
            Список UUID медиа-файлов.
        created_by : UUID | None
            Если указан, фильтрует по создателю.

        Returns
        -------
        list[FileDTO]
            Список найденных медиа-файлов.
        """
        query = (
            select(FileModel)
            .options(selectinload(FileModel.creator))
            .where(FileModel.id.in_(files_ids))
        )

        if created_by:
            query = query.where(FileModel.created_by == created_by)

        files = await self.session.scalars(query)

        return [FileDTO.model_validate(file) for file in files.all()]

    async def get_existing_album_items(
        self, album_id: UUID, files_ids: list[UUID]
    ) -> set[UUID]:
        """Получает UUID медиа-файлов, уже прикреплённых к альбому.

        Parameters
        ----------
        album_id : UUID
            UUID альбома.
        files_ids : list[UUID]
            Список UUID медиа-файлов для проверки.

        Returns
        -------
        set[UUID]
            Множество UUID уже прикреплённых файлов.
        """
        result = await self.session.scalars(
            select(AlbumItemsModel.file_id).where(
                and_(
                    AlbumItemsModel.album_id == album_id,
                    AlbumItemsModel.file_id.in_(files_ids),
                )
            )
        )

        return set(result.all())

    async def attach_files_to_album(
        self, album_id: UUID, files_uuids: list[UUID]
    ) -> None:
        """Прикрепляет медиа-файлы к альбому.

        Parameters
        ----------
        album_id : UUID
            UUID альбома.
        files_uuids : list[UUID]
            Список UUID медиа-файлов для прикрепления.

        Raises
        ------
        MediaNotFoundException
            Если альбом не существует.
        """
        new_items: list[AlbumItemsModel] = [
            AlbumItemsModel(album_id=album_id, file_id=file_id)
            for file_id in files_uuids
        ]

        if new_items:
            self.session.add_all(new_items)
