from uuid import UUID

from sqlalchemy import and_, case, delete, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.album import AlbumModel
from app.models.album_items import AlbumItemsModel
from app.repositories.interface import RepositoryInterface
from app.schemas.dto.album import AlbumDTO, AlbumWithItemsDTO


class AlbumsRepository(RepositoryInterface):
    """Репозиторий медиа-альбомов.

    Реализация паттерна Репозиторий для работы с медиа-альбомами.
    Отвечает за CRUD операции с альбомами и управление связями с файлами.

    Methods
    -------
    add_album(title, description, cover_url, is_private, created_by)
        Добавляет в базу данных новую запись о медиа альбоме.
    get_album_by_id(album_id)
        Возвращает DTO медиа альбома по его id.
    get_album_with_items_by_id(album_id)
        Возвращает DTO медиа альбома с его элементами.
    get_albums_by_creator_id(offset, limit, creator_id)
        Возвращает список DTO медиа альбомов по id их создателя.
    search_albums_by_trigram(search_query, threshold, limit, created_by)
        Производит поиск альбомов по переданному запросу.
    delete_album_by_id(album_id)
        Удаляет запись о медиа альбоме из базы данных.
    get_existing_album_items(album_id, files_ids)
        Получает UUID медиа-файлов, уже прикреплённых к альбому.
    attach_files_to_album(album_id, files_uuids)
        Прикрепляет медиа-файлы к альбому.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    def add_album(
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
            Видимость альбома.
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
        AlbumDTO | None
            DTO записи альбома или None, если альбом не найден.
        """
        album = await self.session.scalar(
            select(AlbumModel)
            .options(selectinload(AlbumModel.creator))
            .where(AlbumModel.id == album_id)
        )

        return AlbumDTO.model_validate(album) if album else None

    async def get_album_with_items_by_id(
        self, album_id: UUID
    ) -> AlbumWithItemsDTO | None:
        """Возвращает DTO медиа альбома по его id с элементами.

        Parameters
        ----------
        album_id : UUID
            UUID альбома.

        Returns
        -------
        AlbumWithItemsDTO | None
            DTO альбома с файлами или None, если альбом не найден.
        """
        album = await self.session.scalar(
            select(AlbumModel)
            .options(
                selectinload(AlbumModel.creator),
                selectinload(AlbumModel.items),
            )
            .where(AlbumModel.id == album_id)
        )

        return AlbumWithItemsDTO.model_validate(album) if album else None

    async def get_albums_by_creator(
        self, offset: int, limit: int, created_by: list[UUID]
    ) -> list[AlbumDTO]:
        """Возвращает список DTO медиа альбомов по id их создателя.

        Parameters
        ----------
        offset : int
            Смещение от начала списка.
        limit : int
            Количество возвращаемых альбомов.
        created_by : list[UUID]
            Список UUID пользователей, чьи альбомы ищутся.

        Returns
        -------
        list[AlbumDTO]
            Список DTO созданных пользователем альбомов.
        """
        albums = await self.session.scalars(
            select(AlbumModel)
            .options(selectinload(AlbumModel.creator))
            .where(AlbumModel.created_by.in_(created_by))
            .order_by(AlbumModel.created_at)
            .slice(offset, offset + limit)
        )

        return [AlbumDTO.model_validate(album) for album in albums.all()]

    async def search_albums_by_trigram(
        self, search_query: str, threshold: float, limit: int, created_by: list[UUID]
    ) -> list[AlbumDTO]:
        """Производит поиск альбомов по переданному запросу.

        Используется гибридный подход с поиском по полному вхождению (ILIKE)
        и по триграммам (% + GIN-индексы). Результат возвращается в порядке
        возрастания сходства с запросом:
        - Первыми возвращаются результаты с полным совпадением;
        - Далее следуют результаты, отсортированные по значению функции `similarity`.

        Parameters
        ----------
        search_query : str
            Поисковый запрос, по которому производится поиск.
        threshold : float
            Порог сходства для поиска по триграммам.
        limit : int
            Максимальное количество, которое необходимо вернуть.
        created_by : list[UUID]
            Список UUID пользователей, по которым ищутся альбомы.

        Returns
        -------
        list[AlbumDTO]
            Список найденных альбомов.
        """
        await self.session.execute(
            text("SELECT set_limit(:threshold)"),
            {"threshold": threshold},
        )

        ilike_pattern = f"%{search_query}%"

        albums = await self.session.scalars(
            select(AlbumModel)
            .options(selectinload(AlbumModel.creator))
            .where(AlbumModel.created_by.in_(created_by))
            .filter(
                or_(
                    # поиск полного вхождения
                    AlbumModel.title.ilike(ilike_pattern),
                    AlbumModel.description.ilike(ilike_pattern),
                    # поиск по триграммам
                    AlbumModel.title.op("%")(search_query),
                    AlbumModel.description.op("%")(search_query),
                )
            )
            .order_by(
                # полные вхождения в списке идут выше
                case(
                    (
                        or_(
                            AlbumModel.title.ilike(ilike_pattern),
                            AlbumModel.description.ilike(ilike_pattern),
                        ),
                        1,
                    ),
                    else_=0,
                ).desc(),
                func.greatest(
                    func.coalesce(func.similarity(AlbumModel.title, search_query), 0.0),
                    func.coalesce(
                        func.similarity(AlbumModel.description, search_query), 0.0
                    ),
                ).desc(),
            )
            .limit(limit)
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

    def attach_files_to_album(self, album_id: UUID, files_uuids: list[UUID]) -> None:
        """Прикрепляет медиа-файлы к альбому.

        Parameters
        ----------
        album_id : UUID
            UUID альбома.
        files_uuids : list[UUID]
            Список UUID медиа-файлов для прикрепления.
        """
        new_items = [
            AlbumItemsModel(album_id=album_id, file_id=file_id)
            for file_id in files_uuids
        ]

        if new_items:
            self.session.add_all(new_items)
