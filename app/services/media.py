from uuid import UUID

from app.infrastructure.postgresql import UnitOfWork
from app.repositories.media import MediaRepository
from app.schemas.dto.album import AlbumDTO


class MediaService:
    """Сервис работы с медиа.

    Реализует бизнес-логику для:
    - Регистрации и получения медиа альбомов;
    - Загрузку и выгрузку различных медиа;
    - Управление медиа внутри и между альбомами.

    Attributes
    ----------
    _media_repo : MediaRepository
        Репозиторий для операций с медиа в БД.

    Methods
    -------
    create_album(title, description, cover_url, is_private, created_by)
        Создание нового альбома.
    get_albums(creator_id)
        Получение всех альбомов по UUID создателя.
    """

    def __init__(self, unit_of_work: UnitOfWork):
        super().__init__()

        self._media_repo: MediaRepository = unit_of_work.get_repository(MediaRepository)

    async def create_album(
        self,
        title: str,
        description: str | None,
        cover_url: str | None,
        is_private: bool,
        created_by: UUID,
    ) -> None:
        """Создание нового альбома.

        Создаёт новый альбом по переданным данным.

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
        await self._media_repo.add_album(
            title, description, cover_url, is_private, created_by
        )

    async def get_albums(self, creator_id: UUID) -> list[AlbumDTO]:
        """Получение всех альбомов по UUID создателя.

        Получает на вход UUID пользователя, возвращает список
        всех альбомов, для которых данный пользователь считается
        создателем.

        Parameters
        ----------
        creator_id : UUID
            UUID пользователя.

        Returns
        -------
        list[AlbumDTO]
            Список альбомов пользователя.
        """
        return await self._media_repo.get_albums_by_creator_id(creator_id)
