from uuid import UUID

from app.core.exceptions.media import MediaNotFoundException
from app.infrastructure.postgresql import UnitOfWork
from app.repositories.media import AlbumsRepository, FilesRepository
from app.schemas.dto.album import AlbumDTO, AlbumWithItemsDTO
from app.schemas.dto.file import FileDTO


class AlbumsService:
    """Сервис работы с медиа-альбомами.

    Реализует бизнес-логику для:
    - Регистрации и получения медиа альбомов;
    - Управления медиа внутри и между альбомами;
    - Привязки медиа-файлов к альбомам.

    Attributes
    ----------
    _albums_repo : AlbumsRepository
        Репозиторий для операций с альбомами в базе данных.
    _files_repo : FilesRepository
        Репозиторий для операций с файлами в базе данных.

    Methods
    -------
    create_album(title, description, cover_url, is_private, created_by)
        Создание нового медиа альбома.
    get_albums(offset, limit, creator_id)
        Получение всех медиа альбомов по UUID создателя.
    get_album(album_id, user_id)
        Получение подробной информации об альбоме по его UUID.
    delete_album(album_id, user_id)
        Удаление альбома по его UUID.
    attach(album_id, files_uuids, user_id)
        Прикрепляет медиа-файлы к альбому.
    """

    def __init__(self, unit_of_work: UnitOfWork):
        super().__init__()

        self._albums_repo: AlbumsRepository = unit_of_work.get_repository(
            AlbumsRepository
        )
        self._files_repo: FilesRepository = unit_of_work.get_repository(FilesRepository)

    async def create_album(
        self,
        title: str,
        description: str | None,
        cover_url: str | None,
        is_private: bool,
        created_by: UUID,
    ) -> None:
        """Создание нового медиа альбома.

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
        self._albums_repo.add_album(
            title, description, cover_url, is_private, created_by
        )

    async def get_albums(
        self, offset: int, limit: int, creator_id: UUID
    ) -> list[AlbumDTO]:
        """Получение всех альбомов по UUID создателя.

        Получает на вход UUID пользователя, возвращает список
        всех альбомов, для которых данный пользователь считается
        создателем.

        Parameters
        ----------
        offset : int
            Смещение от начала списка (количество пропускаемых альбомов).
        limit : int
            Количество возвращаемых альбомов.
        creator_id : UUID
            UUID пользователя.

        Returns
        -------
        list[AlbumDTO]
            Список альбомов пользователя.
        """
        return await self._albums_repo.get_albums_by_creator_id(
            offset, limit, creator_id
        )

    async def get_album(self, album_id: UUID, user_id: UUID) -> AlbumWithItemsDTO:
        """Получение подробной информации об альбоме по его UUID.

        Получает на вход UUID медиа-альбома и UUID текущего пользователя,
        возвращает DTO медиа-альбома с подробным представлением входящих
        в него медиа-файлов.

        Parameters
        ----------
        album_id : UUID
            UUID медиа-альбома к получению.
        user_id : UUID
            UUID текущего пользователя.

        Returns
        -------
        AlbumWithItemsDTO
            Подробный DTO медиа-альбома.

        Raises
        ------
        MediaNotFoundException
            В случае если альбом по переданному UUID не существует или
            текущий пользователь не имеет прав на просмотр этого альбома.
        """
        album: (
            AlbumWithItemsDTO | None
        ) = await self._albums_repo.get_album_with_items_by_id(album_id)

        if album is None or album.creator.id != user_id:
            raise MediaNotFoundException(
                media_type="album",
                detail=f"Album with id={album_id} not found, or you're not this album's creator.",
            )

        return album

    async def search_albums(
        self, search_query: str, threshold: float, limit: int, created_by: UUID
    ) -> list[AlbumDTO]:
        return await self._albums_repo.search_albums_by_trigram(
            search_query, threshold, limit, created_by
        )

    async def delete_album(self, album_id: UUID, user_id: UUID) -> None:
        """Удаление альбома по его UUID.

        Получает UUID альбома и UUID пользователя, совершающего действие удаления.
        Если UUID пользователя не совпадает с UUID создателя альбома, завершает
        действие исключением. В ином случае удаляет альбом.

        Parameters
        ----------
        album_id : UUID
            UUID альбома к удалению.
        user_id : UUID
            UUID пользователя, запрашивающего удаление.

        Raises
        ------
        MediaNotFoundException
            Возникает в случае, если альбом с переданным UUID не существует
            или текущий пользователь не является создателем альбома.
        """
        album: AlbumDTO | None = await self._albums_repo.get_album_by_id(album_id)

        if album is None or album.creator.id != user_id:
            raise MediaNotFoundException(
                media_type="album",
                detail=f"Album with id={album_id} not found, or you're not this album's creator.",
            )

        await self._albums_repo.delete_album_by_id(album_id)

    async def attach(
        self, album_id: UUID, files_uuids: list[UUID], user_id: UUID
    ) -> None:
        """Прикрепляет медиа-файлы к альбому.

        Проверяет:
        1. Существование альбома;
        2. Права пользователя на альбом (должен быть создателем);
        3. Существование всех медиа-файлов;
        4. Права пользователя на медиа-файлы (должен быть создателем).

        Parameters
        ----------
        album_id : UUID
            UUID альбома.
        files_uuids : list[UUID]
            Список UUID медиа-файлов для прикрепления.
        user_id : UUID
            UUID пользователя, выполняющего операцию.

        Raises
        ------
        MediaNotFoundException
            Если альбом не существует или не все медиа-файлы найдены.
        """
        album: AlbumDTO | None = await self._albums_repo.get_album_by_id(album_id)

        if album is None or album.creator.id != user_id:
            raise MediaNotFoundException(
                media_type="album",
                detail=f"Album with id={album_id} not found, or you're not this album's creator.",
            )

        if not files_uuids:
            return

        files: list[FileDTO] = await self._files_repo.get_files_by_ids(
            files_uuids, created_by=user_id
        )
        found_files_ids: set[UUID] = {file.id for file in files}

        if len(found_files_ids) != len(files_uuids):
            missing_ids: set[UUID] = set(files_uuids) - found_files_ids

            missing_list: str = ", ".join(str(mid) for mid in missing_ids)
            raise MediaNotFoundException(
                media_type="file",
                detail=(
                    "One or more media files not found or you don't have "
                    f"permission to attach them. Missing IDs: {missing_list}"
                ),
            )

        attached_files: set[UUID] = await self._albums_repo.get_existing_album_items(
            album_id, files_uuids
        )

        self._albums_repo.attach_files_to_album(
            album_id, list(set(files_uuids) - attached_files)
        )
