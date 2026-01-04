from typing import Any
from uuid import UUID

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.album import AlbumModel
from app.models.album_items import AlbumItemsModel
from app.models.media import MediaModel, MediaType
from app.repositories.interface import RepositoryInterface
from app.schemas.dto.album import AlbumDTO, AlbumWithItemsDTO
from app.schemas.dto.media import MediaDTO


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
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def add_file(
        self,
        url: str,
        type_: MediaType,
        created_by: UUID,
        title: str | None = None,
        description: str | None = None,
        geo_data: dict[str, Any] | None = None,
    ) -> None:
        """Добавляет в базу данных новую запись о медиа файле.

        Parameters
        ----------
        url : str
            URL файла.
        type_ : MediaType
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
            MediaModel(
                url=url,
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

    async def get_media_by_ids(
        self, media_ids: list[UUID], created_by: UUID | None = None
    ) -> list[MediaDTO]:
        """Получает медиа-файлы по списку UUID.

        Parameters
        ----------
        media_ids : list[UUID]
            Список UUID медиа-файлов.
        created_by : UUID | None
            Если указан, фильтрует по создателю.

        Returns
        -------
        list[MediaDTO]
            Список найденных медиа-файлов.
        """
        query = (
            select(MediaModel)
            .options(selectinload(MediaModel.creator))
            .where(MediaModel.id.in_(media_ids))
        )

        if created_by:
            query = query.where(MediaModel.created_by == created_by)

        medias = await self.session.scalars(query)

        return [MediaDTO.model_validate(media) for media in medias.all()]

    async def get_existing_album_items(
        self, album_id: UUID, media_ids: list[UUID]
    ) -> set[UUID]:
        """Получает UUID медиа-файлов, уже прикреплённых к альбому.

        Parameters
        ----------
        album_id : UUID
            UUID альбома.
        media_ids : list[UUID]
            Список UUID медиа-файлов для проверки.

        Returns
        -------
        set[UUID]
            Множество UUID уже прикреплённых файлов.
        """
        result = await self.session.scalars(
            select(AlbumItemsModel.media_id).where(
                and_(
                    AlbumItemsModel.album_id == album_id,
                    AlbumItemsModel.media_id.in_(media_ids),
                )
            )
        )

        return set(result.all())

    async def attach_media_to_album(
        self, album_id: UUID, media_uuids: list[UUID]
    ) -> None:
        """Прикрепляет медиа-файлы к альбому.

        Parameters
        ----------
        album_id : UUID
            UUID альбома.
        media_uuids : list[UUID]
            Список UUID медиа-файлов для прикрепления.

        Raises
        ------
        MediaNotFoundException
            Если альбом не существует.
        """
        new_items: list[AlbumItemsModel] = [
            AlbumItemsModel(album_id=album_id, media_id=media_id)
            for media_id in media_uuids
        ]

        if new_items:
            self.session.add_all(new_items)
