from uuid import UUID

from app.core.exceptions.media import MediaNotFoundException
from app.infrastructure.postgresql import UnitOfWork
from app.repositories.couples import CouplesRepository
from app.repositories.media import AlbumsRepository, FilesRepository
from app.schemas.dto.album import AlbumDTO, AlbumWithItemsDTO


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
    search_albums(search_query, threshold, limit, created_by)
        Производит поиск альбомов по переданному запросу.
    get_album(album_id, user_id)
        Получение подробной информации об альбоме по его UUID.
    update_album(album_id, title, description, cover_url, is_private, user_id)
        Обновление атрибутов медиа-альбома по его UUID.
    delete_album(album_id, user_id)
        Удаление альбома по его UUID.
    attach(album_id, files_uuids, user_id)
        Прикрепляет медиа-файлы к альбому.
    detach(album_id, files_uuids, user_id)
        Открепляет медиа-файлы от альбома.
    """

    def __init__(self, unit_of_work: UnitOfWork):
        super().__init__()

        self._albums_repo = unit_of_work.get_repository(AlbumsRepository)
        self._files_repo = unit_of_work.get_repository(FilesRepository)
        self._couples_repo = unit_of_work.get_repository(CouplesRepository)

    def create_album(
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
        self, offset: int, limit: int, user_id: UUID
    ) -> tuple[list[AlbumDTO], int]:
        """Получение всех альбомов по UUID создателя.

        Получает на вход UUID пользователя, ищет UUID партнёра,
        возвращает список всех альбомов, которые доступны пользователю (
        созданы им или его партнёром).

        Parameters
        ----------
        offset : int
            Смещение от начала списка (количество пропускаемых альбомов).
        limit : int
            Количество возвращаемых альбомов.
        user_id : UUID
            UUID пользователя.

        Returns
        -------
        tuple[list[AlbumDTO], int]
            Кортеж из списка альбомов и общего количества.
        """
        partner_id = await self._couples_repo.get_partner_id_by_user_id(user_id)

        return await self._albums_repo.get_albums_by_creator(
            offset, limit, user_id, partner_id
        )

    async def search_albums(
        self, search_query: str, threshold: float, limit: int, user_id: UUID
    ) -> tuple[list[AlbumDTO], int]:
        """Поиск альбомов по переданному запросу.

        Получает на вход поисковой запрос, параметры поиска и UUID пользователя,
        возвращает список альбомов этого пользователя и его партнёра,
        для которых поиск по запросу удовлетворяет параметрам.

        Parameters
        ----------
        search_query : str
            Поисковый запрос, по которому производится поиск.
        threshold : float
            Порог сходства для поиска по триграммам.
        limit : int
            Максимальное количество, которое необходимо вернуть.
        user_id : UUID
            UUID текущего пользователя.

        Returns
        -------
        tuple[list[AlbumDTO], int]
            Кортеж из списка найденных альбомов и общего количества.
        """
        partner_id = await self._couples_repo.get_partner_id_by_user_id(user_id)

        return await self._albums_repo.search_albums_by_trigram(
            search_query, threshold, limit, user_id, partner_id
        )

    async def get_album(
        self, album_id: UUID, offset: int, limit: int, user_id: UUID
    ) -> AlbumWithItemsDTO:
        """Получение подробной информации об альбоме по его UUID.

        Получает на вход UUID медиа-альбома и UUID текущего пользователя,
        возвращает DTO медиа-альбома с подробным представлением входящих
        в него медиа-файлов.

        Parameters
        ----------
        album_id : UUID
            UUID медиа-альбома к получению.
        offset : int
            Смещение для пагинации.
        limit : int | None
            Лимит количества элементов.
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
        partner_id = await self._couples_repo.get_partner_id_by_user_id(user_id)

        album = await self._albums_repo.get_album_with_items_by_id(
            album_id, offset, limit, user_id, partner_id
        )

        if album is None:
            raise MediaNotFoundException(
                media_type="album",
                detail=f"Album with id={album_id} not found, or you're lack of rights.",
            )

        return album

    async def update_album(
        self,
        album_id: UUID,
        title: str,
        description: str | None,
        cover_url: str | None,
        is_private: bool,
        user_id: UUID,
    ) -> None:
        """Обновление атрибутов медиа-альбома по его UUID.

        Получает идентификатор партнера текущего пользователя и передает данные
        в репозиторий для обновления альбома с учетом прав доступа.

        Parameters
        ----------
        album_id : UUID
            UUID альбома к изменению.
        title : str
            Новый заголовок альбома.
        description : str | None
            Новое описание альбома или None для сохранения текущего значения.
        cover_url : str | None
            Новая ссылка на обложку альбома или None для сброса обложки.
        is_private : bool
            Новый статус приватности альбома.
        user_id : UUID
            UUID пользователя, инициирующего изменение альбома.
        """
        partner_id = await self._couples_repo.get_partner_id_by_user_id(user_id)

        album = await self._albums_repo.get_album_by_id(album_id, user_id, partner_id)

        if album is None:
            raise MediaNotFoundException(
                media_type="album",
                detail=f"Album with id={album_id} not found, or you're not this album's creator.",
            )

        await self._albums_repo.update_album_by_id(
            album_id, title, description, cover_url, is_private
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
        album = await self._albums_repo.get_album_by_id(album_id, user_id)

        if album is None:
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
        2. Права пользователя на альбом (должен быть создателем или партнёром создателя);
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
        partner_id = await self._couples_repo.get_partner_id_by_user_id(user_id)

        album = await self._albums_repo.get_album_by_id(album_id, user_id, partner_id)

        if album is None:
            raise MediaNotFoundException(
                media_type="album",
                detail=f"Album with id={album_id} not found, or you're lack of rights.",
            )

        if not files_uuids:
            return

        received_files_uuids = set(files_uuids)

        files = await self._files_repo.get_files_by_ids(files_uuids, user_id)
        found_files_uuids = {file.id for file in files}

        if received_files_uuids != found_files_uuids:
            missing_uuids = received_files_uuids - found_files_uuids

            missing_list = ", ".join(str(muuid) for muuid in missing_uuids)
            raise MediaNotFoundException(
                media_type="file",
                detail=(
                    "One or more media files not found or you don't have "
                    f"permission to attach them. Missing IDs: {missing_list}"
                ),
            )

        attached_files_uuids = await self._albums_repo.get_existing_album_items(
            album_id, files_uuids
        )

        self._albums_repo.attach_files_to_album(
            album_id, list(received_files_uuids - attached_files_uuids)
        )

    async def detach(
        self, album_id: UUID, files_uuids: list[UUID], user_id: UUID
    ) -> None:
        """Открепляет медиа-файлы от альбома.

        Проверяет:
        1. Существование альбома;
        2. Права пользователя на альбом (должен быть создателем или партнёром создателя);
        3. Прикрепление всех медиа-файлов;
        4. Права пользователя на медиа-файлы (должен быть создателем).

        Parameters
        ----------
        album_id : UUID
            UUID альбома.
        files_uuids : list[UUID]
            Список UUID медиа-файлов для открепления.
        user_id : UUID
            UUID пользователя, выполняющего операцию.

        Raises
        ------
        MediaNotFoundException
            Если альбом не существует или не все медиа-файлы найдены.
        """
        partner_id = await self._couples_repo.get_partner_id_by_user_id(user_id)

        album = await self._albums_repo.get_album_by_id(album_id, user_id, partner_id)

        if album is None:
            raise MediaNotFoundException(
                media_type="album",
                detail=f"Album with id={album_id} not found, or you're lack of rights.",
            )

        if not files_uuids:
            return

        received_files_uuids = set(files_uuids)
        attached_files_uuids = await self._albums_repo.get_existing_album_items(
            album_id, files_uuids
        )

        if attached_files_uuids != received_files_uuids:
            missing_uuids = received_files_uuids - attached_files_uuids

            missing_list = ", ".join(str(muuid) for muuid in missing_uuids)
            raise MediaNotFoundException(
                media_type="file",
                detail=(
                    "One or more media files are not attached to media album. "
                    f"Missing IDs: {missing_list}"
                ),
            )

        await self._albums_repo.detach_files_from_album(
            album_id, list(received_files_uuids)
        )
