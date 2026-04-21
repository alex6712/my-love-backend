from uuid import UUID

from app.core.enums import SortOrder
from app.core.exceptions.base import NothingToUpdateException
from app.core.exceptions.media import MediaNotFoundException
from app.infra.postgres.uow import UnitOfWork
from app.repositories.couple import CoupleRepository
from app.repositories.interface import AccessContext
from app.repositories.media import AlbumRepository, FileRepository
from app.schemas.dto.album import (
    AlbumDTO,
    AlbumWithItemsDTO,
    CreateAlbumDTO,
    UpdateAlbumDTO,
)


class AlbumService:
    """Сервис работы с медиа-альбомами.

    Реализует бизнес-логику для:
    - Регистрации и получения медиа альбомов;
    - Управления медиа внутри и между альбомами;
    - Привязки медиа-файлов к альбомам.

    Attributes
    ----------
    _album_repo : AlbumRepository
        Репозиторий для операций с альбомами в базе данных.
    _file_repo : FileRepository
        Репозиторий для операций с файлами в базе данных.
    _couple_repo : CoupleRepository
        Репозиторий для операций с парами пользователей в БД.

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
        self._album_repo = unit_of_work.get_repository(AlbumRepository)
        self._file_repo = unit_of_work.get_repository(FileRepository)
        self._couple_repo = unit_of_work.get_repository(CoupleRepository)

    async def create_album(self, create_dto: CreateAlbumDTO, created_by: UUID) -> None:
        """Создание нового медиа альбома.

        Parameters
        ----------
        create_dto : CreateAlbumDTO
            Данные для создания альбома.
        created_by : UUID
            UUID пользователя, создавшего альбом.
        """
        await self._album_repo.create(create_dto, created_by)

    async def get_albums(
        self,
        offset: int,
        limit: int,
        sort_order: SortOrder,
        user_id: UUID,
        partner_id: UUID | None,
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
        sort_order : SortOrder
            Направление сортировки альбомов.
        user_id : UUID
            UUID пользователя.
        partner_id : UUID | None
            UUID партнёра пользователя или None.

        Returns
        -------
        tuple[list[AlbumDTO], int]
            Кортеж из списка альбомов и общего количества.
        """
        return await self._album_repo.get_all(
            AccessContext(user_id=user_id, partner_id=partner_id),
            offset=offset,
            limit=limit,
            sort_order=sort_order,
        )

    async def search_albums(
        self,
        search_query: str,
        threshold: float,
        offset: int,
        limit: int,
        user_id: UUID,
        partner_id: UUID | None,
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
        offset : int
            Смещение от начала списка (количество пропускаемых альбомов).
        limit : int
            Максимальное количество, которое необходимо вернуть.
        user_id : UUID
            UUID текущего пользователя.
        partner_id : UUID | None
            UUID партнёра пользователя или None.

        Returns
        -------
        tuple[list[AlbumDTO], int]
            Кортеж из списка найденных альбомов и общего количества.
        """
        return await self._album_repo.search_by_trigram(
            AccessContext(user_id=user_id, partner_id=partner_id),
            search_query,
            threshold,
            offset=offset,
            limit=limit,
        )

    async def get_album(
        self,
        album_id: UUID,
        offset: int,
        limit: int,
        user_id: UUID,
        partner_id: UUID | None,
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
        partner_id : UUID | None
            UUID партнёра пользователя или None.

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
        album = await self._album_repo.get_with_items(
            album_id,
            AccessContext(user_id=user_id, partner_id=partner_id),
            offset=offset,
            limit=limit,
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
        update_dto: UpdateAlbumDTO,
        user_id: UUID,
        partner_id: UUID | None,
    ) -> None:
        """Частичное обновление атрибутов медиа-альбома по его UUID.

        Получает идентификатор партнёра текущего пользователя и передаёт данные
        в репозиторий для обновления альбома с учётом прав доступа.
        Обновляет только явно переданные поля (не равные `UNSET`).

        Parameters
        ----------
        album_id : UUID
            UUID альбома к изменению.
        update_dto : UpdateAlbumDTO
            DTO с полями для обновления. Содержит только явно переданные поля.
        user_id : UUID
            UUID пользователя, инициирующего изменение альбома.
        partner_id : UUID | None
            UUID партнёра пользователя или None.

        Raises
        ------
        NothingToUpdateException
            Не было передано ни одного поля на обновление.
        MediaNotFoundException
            Если альбом не найден или пользователь не является его создателем.
        """
        if update_dto.is_empty():
            raise NothingToUpdateException(detail="No fields provided for update.")

        if not await self._album_repo.update(
            album_id, update_dto, AccessContext(user_id=user_id, partner_id=partner_id)
        ):
            raise MediaNotFoundException(
                media_type="album",
                detail=f"Album with id={album_id} not found, or you're not this album's creator.",
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
        if not await self._album_repo.delete(album_id, AccessContext(user_id=user_id)):
            raise MediaNotFoundException(
                media_type="album",
                detail=f"Album with id={album_id} not found, or you're not this album's creator.",
            )

    async def attach_files(
        self,
        album_id: UUID,
        files_ids: list[UUID],
        user_id: UUID,
        partner_id: UUID | None,
    ) -> None:
        """Прикрепляет медиа-файлы к альбому.

        Не добавляет файлы, если они не существуют, пользователь
        не имеет прав на операции с ними или они уже прикреплены
        к указанному альбому.

        Parameters
        ----------
        album_id : UUID
            UUID альбома.
        files_ids : list[UUID]
            Список UUID медиа-файлов для прикрепления.
        user_id : UUID
            UUID пользователя, выполняющего операцию.
        partner_id : UUID | None
            UUID партнёра пользователя, если есть.

        Raises
        ------
        MediaNotFoundException
            Если альбом недоступен или у пользователя нет прав
            на один или несколько файлов.
        """
        if not files_ids:
            return

        access_ctx = AccessContext(user_id=user_id, partner_id=partner_id)

        if not await self._album_repo.get_by_id(album_id, access_ctx):
            raise MediaNotFoundException(
                media_type="album",
                detail=f"Album with id={album_id} not found, or you're lack of rights.",
            )

        await self._album_repo.attach_files(album_id, files_ids, access_ctx)

    async def detach_files(
        self,
        album_id: UUID,
        files_ids: list[UUID],
        user_id: UUID,
        partner_id: UUID | None,
    ) -> None:
        """Открепляет медиа-файлы от альбома.

        Не открепляет файлы, если они не существуют, пользователь
        не имеет прав на операции с ними или они не прикреплены
        к указанному альбому.

        Сначала пытается открепить все файлы единым запросом.
        Если часть файлов не была откреплена, выполняет диагностику:
        проверяет доступность альбома и наличие файлов в нём.

        Parameters
        ----------
        album_id : UUID
            UUID альбома.
        files_ids : list[UUID]
            Список UUID медиа-файлов для открепления.
        user_id : UUID
            UUID пользователя, выполняющего операцию.
        partner_id : UUID | None
            UUID партнёра пользователя, если есть.

        Raises
        ------
        MediaNotFoundException
            Если альбом недоступен или один или несколько файлов
            не прикреплены к альбому.
        """
        if not files_ids:
            return

        access_ctx = AccessContext(user_id=user_id, partner_id=partner_id)

        if not await self._album_repo.get_by_id(album_id, access_ctx):
            raise MediaNotFoundException(
                media_type="album",
                detail=f"Album with id={album_id} not found, or you're lack of rights.",
            )

        await self._album_repo.detach_files(album_id, files_ids, access_ctx)
