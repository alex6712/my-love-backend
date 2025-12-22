from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import MediaNotFoundException
from app.models.album import AlbumModel
from app.repositories.interface import RepositoryInterface
from app.schemas.dto.album import AlbumDTO


class MediaRepository(RepositoryInterface):
    """Репозиторий медиа альбомов и файлов.

    Реализация паттерна Репозиторий. Является объектом доступа к данным (DAO).
    Реализует основные CRUD операции с различными типами медиа.

    Methods
    -------
    add_album(title, description, cover_url, is_private, created_by)
        Добавляет в базу данных новую запись о медиа альбоме.
    get_album_by_id(id_)
        Возвращает DTO медиа альбома по его id.
    get_albums_by_creator_id(creator_id)
        Возвращает список DTO медиа альбомов по id их создателя.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session)

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

    async def get_album_by_id(self, id_: UUID) -> AlbumDTO:
        """Возвращает DTO медиа альбома по его id.

        Parameters
        ----------
        id_ : UUID
            UUID альбома.

        Returns
        -------
        AlbumDTO
            DTO записи альбома.
        """
        album: AlbumModel | None = await self.session.scalar(
            select(AlbumModel).where(AlbumModel.id == id_)
        )

        if album is None:
            raise MediaNotFoundException(detail=f"Media album with id={id_} not found.")

        return AlbumDTO.model_validate(album)

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
            select(AlbumModel).where(AlbumModel.created_by == creator_id)
        )

        return [AlbumDTO.model_validate(album) for album in albums.all()]
