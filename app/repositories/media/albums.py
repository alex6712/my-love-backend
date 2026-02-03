import asyncio
from uuid import UUID

from sqlalchemy import and_, case, delete, func, insert, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.album import AlbumModel
from app.models.album_items import AlbumItemsModel
from app.models.file import FileModel
from app.repositories.interface import SharedResourceRepository
from app.schemas.dto.album import AlbumDTO, AlbumWithItemsDTO


class AlbumsRepository(SharedResourceRepository):
    """Репозиторий медиа-альбомов.

    Реализация паттерна Репозиторий для работы с медиа-альбомами.
    Отвечает за CRUD операции с альбомами и управление связями с файлами.

    Methods
    -------
    add_album(title, description, cover_url, is_private, created_by)
        Добавляет в базу данных новую запись о медиа альбоме.
    get_album_by_id(album_id, user_id, partner_id)
        Возвращает DTO медиа альбома по его id.
    get_albums_by_creator(offset, limit, user_id, partner_id)
        Возвращает список DTO медиа альбомов по id их создателя.
    search_albums_by_trigram(search_query, threshold, limit, user_id, partner_id)
        Производит поиск альбомов по переданному запросу.
    get_album_with_items_by_id(album_id, user_id, partner_id)
        Возвращает DTO медиа альбома с его элементами.
    update_album_by_id(album_id, title, description, cover_url, is_private)
        Обновление атрибутов альбома в базе данных.
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

    async def get_album_by_id(
        self, album_id: UUID, user_id: UUID, partner_id: UUID | None = None
    ) -> AlbumDTO | None:
        """Возвращает DTO медиа альбома по его id.

        Parameters
        ----------
        album_id : UUID
            UUID альбома.
        user_id : UUID
            UUID текущего пользователя.
        partner_id : UUID | None, optional
            UUID партнёра текущего пользователя.

        Returns
        -------
        AlbumDTO | None
            DTO записи альбома или None, если альбом не найден.
        """
        album = await self.session.scalar(
            select(AlbumModel)
            .options(selectinload(AlbumModel.creator))
            .where(
                AlbumModel.id == album_id,
                self._build_shared_clause(AlbumModel, user_id, partner_id),
            )
        )

        return AlbumDTO.model_validate(album) if album else None

    async def get_albums_by_creator(
        self, offset: int, limit: int, user_id: UUID, partner_id: UUID | None = None
    ) -> tuple[list[AlbumDTO], int]:
        """Возвращает список DTO медиа альбомов по id их создателя.

        Parameters
        ----------
        offset : int
            Смещение от начала списка.
        limit : int
            Количество возвращаемых альбомов.
        user_id : UUID
            UUID текущего пользователя.
        partner_id : UUID | None, optional
            UUID партнёра текущего пользователя.

        Returns
        -------
        tuple[list[AlbumDTO], int]
            Кортеж из списка DTO альбомов и общего количества.
        """
        query = (
            select(AlbumModel)
            .options(selectinload(AlbumModel.creator))
            .order_by(AlbumModel.created_at)
            .slice(offset, offset + limit)
        )

        where_clause = self._build_shared_clause(AlbumModel, user_id, partner_id)

        query = query.where(where_clause)
        count_query = self._build_count_query(AlbumModel, where_clause)

        albums, total = await asyncio.gather(
            self.session.scalars(query),
            self.session.scalar(count_query),
        )

        return [AlbumDTO.model_validate(album) for album in albums.all()], total or 0

    async def search_albums_by_trigram(
        self,
        search_query: str,
        threshold: float,
        offset: int,
        limit: int,
        user_id: UUID,
        partner_id: UUID | None = None,
    ) -> tuple[list[AlbumDTO], int]:
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
        offset : int
            Смещение от начала списка (количество пропускаемых альбомов).
        limit : int
            Максимальное количество, которое необходимо вернуть.
        user_id : UUID
            UUID текущего пользователя.
        partner_id : UUID | None, optional
            UUID партнёра текущего пользователя.

        Returns
        -------
        tuple[list[AlbumDTO], int]
            Кортеж из списка найденных альбомов и общего количества.
        """
        await self.session.execute(
            text("SELECT set_limit(:threshold)"),
            {"threshold": threshold},
        )

        ilike_pattern = f"%{search_query}%"

        ilikes = [
            AlbumModel.title.ilike(ilike_pattern),
            AlbumModel.description.ilike(ilike_pattern),
        ]

        query = (
            select(AlbumModel)
            .options(selectinload(AlbumModel.creator))
            .order_by(
                # полные вхождения в списке идут выше
                case((or_(*ilikes), 1.0), else_=0.0).desc(),
                func.greatest(
                    func.coalesce(func.similarity(AlbumModel.title, search_query), 0.0),
                    func.coalesce(
                        func.similarity(AlbumModel.description, search_query), 0.0
                    ),
                ).desc(),
                AlbumModel.created_at,
            )
            .slice(offset, offset + limit)
        )

        where_clauses = [self._build_shared_clause(AlbumModel, user_id, partner_id)]
        where_clauses.extend(
            [
                # поиск полного вхождения
                *ilikes,
                # поиск по триграммам
                AlbumModel.title.op("%")(search_query),
                AlbumModel.description.op("%")(search_query),
            ]
        )

        query = query.where(*where_clauses)
        count_query = self._build_count_query(AlbumModel, *where_clauses)

        albums, total = await asyncio.gather(
            self.session.scalars(query),
            self.session.scalar(count_query),
        )

        return [AlbumDTO.model_validate(album) for album in albums.all()], total or 0

    async def get_album_with_items_by_id(
        self,
        album_id: UUID,
        offset: int,
        limit: int,
        user_id: UUID,
        partner_id: UUID | None = None,
    ) -> AlbumWithItemsDTO | None:
        """Возвращает DTO медиа альбома по его id с элементами.

        Parameters
        ----------
        album_id : UUID
            UUID альбома.
        offset : int
            Смещение для пагинации.
        limit : int | None
            Лимит количества элементов.
        user_id : UUID
            UUID текущего пользователя.
        partner_id : UUID | None, optional
            UUID партнёра текущего пользователя.

        Returns
        -------
        AlbumWithItemsDTO | None
            DTO альбома с файлами или None, если альбом не найден.
        """
        album_query = (
            select(AlbumModel)
            .options(selectinload(AlbumModel.creator))
            .where(
                AlbumModel.id == album_id,
                self._build_shared_clause(AlbumModel, user_id, partner_id),
            )
        )

        where_clause = AlbumItemsModel.album_id == album_id

        items_query = (
            select(FileModel)
            .join(AlbumItemsModel, AlbumItemsModel.file_id == FileModel.id)
            .where(where_clause)
            .options(selectinload(FileModel.creator))
            .order_by(AlbumItemsModel.created_at)
            .slice(offset, offset + limit)
        )

        count_query = self._build_count_query(AlbumItemsModel, where_clause)

        album, items, total = await asyncio.gather(
            self.session.scalar(album_query),
            self.session.scalars(items_query),
            self.session.scalar(count_query),
        )

        if not album:
            return None

        album_dto = AlbumDTO.model_validate(album)

        return AlbumWithItemsDTO.model_validate(
            {**album_dto.model_dump(), "items": items.all(), "total": total or 0}
        )

    async def update_album_by_id(
        self,
        album_id: UUID,
        title: str,
        description: str | None,
        cover_url: str | None,
        is_private: bool,
    ) -> None:
        """Обновление атрибутов альбома в базе данных.

        Выполняет SQL-запрос UPDATE для изменения атрибутов альбома,
        фильтруя записи по идентификатору альбома и правам создателя.

        Parameters
        ----------
        album_id : UUID
            UUID альбома к изменению.
        title : str
            Новое значение заголовка альбома.
        description : str | None
            Новое значение описания альбома.
        cover_url : str | None
            Новая ссылка на обложку альбома.
        is_private : bool
            Новый статус приватности альбома.
        """
        await self.session.execute(
            update(AlbumModel)
            .where(AlbumModel.id == album_id)
            .values(
                title=title,
                description=description,
                cover_url=cover_url,
                is_private=is_private,
            )
        )

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
        """
        await self.session.execute(
            insert(AlbumItemsModel).values(
                [
                    {
                        "album_id": album_id,
                        "file_id": file_id,
                    }
                    for file_id in files_uuids
                ]
            )
        )

    async def detach_files_from_album(
        self, album_id: UUID, files_uuids: list[UUID]
    ) -> None:
        """Открепляет медиа-файлы от альбома.

        Parameters
        ----------
        album_id : UUID
            UUID альбома.
        files_uuids : list[UUID]
            Список UUID медиа-файлов для удаления.
        """
        await self.session.execute(
            delete(AlbumItemsModel).where(
                and_(
                    AlbumItemsModel.album_id == album_id,
                    AlbumItemsModel.file_id.in_(files_uuids),
                )
            )
        )
