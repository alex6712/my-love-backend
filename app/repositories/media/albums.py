from typing import Any, Protocol, Self, TypeVar
from uuid import UUID

from sqlalchemy import and_, case, delete, func, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.album import AlbumModel
from app.models.album_items import AlbumItemsModel
from app.models.file import FileModel
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
    get_album_by_id(album_id, user_id, partner_id)
        Возвращает DTO медиа альбома по его id.
    get_albums_by_creator(offset, limit, user_id, partner_id)
        Возвращает список DTO медиа альбомов по id их создателя.
    search_albums_by_trigram(search_query, threshold, limit, user_id, partner_id)
        Производит поиск альбомов по переданному запросу.
    get_album_with_items_by_id(album_id, user_id, partner_id)
        Возвращает DTO медиа альбома с его элементами.
    update_album_by_id(album_id, title, description, cover_url, is_private, user_id, partner_id)

    delete_album_by_id(album_id)
        Удаляет запись о медиа альбоме из базы данных.
    get_existing_album_items(album_id, files_ids)
        Получает UUID медиа-файлов, уже прикреплённых к альбому.
    attach_files_to_album(album_id, files_uuids)
        Прикрепляет медиа-файлы к альбому.
    """

    class _HasWhere(Protocol):
        def where(self, *clauses: Any) -> Self: ...

    _Q = TypeVar("_Q", bound=_HasWhere)
    """Generic-тип для обозначения запроса с возможностью модификации WHERE."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    @staticmethod
    def _insert_creator_in_query(
        query: _Q, user_id: UUID, partner_id: UUID | None = None
    ) -> _Q:
        """Добавляет фильтр по создателю в SQL-запрос.

        Модифицирует переданный SQLAlchemy запрос, добавляя условие фильтрации
        по полю `created_by`. В зависимости от наличия `partner_id` применяет
        разные условия фильтрации.

        Parameters
        ----------
        query : _Q
            Исходный SQLAlchemy запрос для модификации.
        user_id : UUID
            Уникальный идентификатор основного пользователя.
        partner_id : UUID | None, optional
            Уникальный идентификатор партнера. Если передан, запрос будет
            фильтровать по обоим идентификаторам (user_id И partner_id).
            По умолчанию None.

        Returns
        -------
        _Q
            Модифицированный SQLAlchemy запрос с добавленным условием WHERE.

        Notes
        -----
        1. Если `partner_id` не передан, используется строгое равенство
           с `user_id` (AlbumModel.created_by == user_id).
        2. Если `partner_id` передан, используется оператор IN с двумя
           значениями (AlbumModel.created_by.in_([user_id, partner_id])).
        3. Метод не изменяет исходный запрос, а возвращает новый объект
           запроса с добавленными условиями.
        """
        if partner_id:
            query = query.where(AlbumModel.created_by.in_([user_id, partner_id]))
        else:
            query = query.where(AlbumModel.created_by == user_id)

        return query

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
        query = (
            select(AlbumModel)
            .options(selectinload(AlbumModel.creator))
            .where(AlbumModel.id == album_id)
        )
        query = AlbumsRepository._insert_creator_in_query(query, user_id, partner_id)

        album = await self.session.scalar(query)

        return AlbumDTO.model_validate(album) if album else None

    async def get_albums_by_creator(
        self, offset: int, limit: int, user_id: UUID, partner_id: UUID | None = None
    ) -> list[AlbumDTO]:
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
        list[AlbumDTO]
            Список DTO созданных пользователем альбомов.
        """
        query = (
            select(AlbumModel)
            .options(selectinload(AlbumModel.creator))
            .order_by(AlbumModel.created_at)
            .slice(offset, offset + limit)
        )
        query = AlbumsRepository._insert_creator_in_query(query, user_id, partner_id)

        albums = await self.session.scalars(query)

        return [AlbumDTO.model_validate(album) for album in albums.all()]

    async def search_albums_by_trigram(
        self,
        search_query: str,
        threshold: float,
        limit: int,
        user_id: UUID,
        partner_id: UUID | None = None,
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
        user_id : UUID
            UUID текущего пользователя.
        partner_id : UUID | None, optional
            UUID партнёра текущего пользователя.

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

        query = (
            select(AlbumModel)
            .options(selectinload(AlbumModel.creator))
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
                AlbumModel.created_at,
            )
            .limit(limit)
        )
        query = AlbumsRepository._insert_creator_in_query(query, user_id, partner_id)

        albums = await self.session.scalars(query)

        return [AlbumDTO.model_validate(album) for album in albums.all()]

    async def get_album_with_items_by_id(
        self, album_id: UUID, user_id: UUID, partner_id: UUID | None = None
    ) -> AlbumWithItemsDTO | None:
        """Возвращает DTO медиа альбома по его id с элементами.

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
        AlbumWithItemsDTO | None
            DTO альбома с файлами или None, если альбом не найден.
        """
        query = (
            select(AlbumModel)
            .options(
                selectinload(AlbumModel.creator),
                selectinload(AlbumModel.items).selectinload(FileModel.creator),
            )
            .where(AlbumModel.id == album_id)
        )
        query = AlbumsRepository._insert_creator_in_query(query, user_id, partner_id)

        album = await self.session.scalar(query)

        return AlbumWithItemsDTO.model_validate(album) if album else None

    async def update_album_by_id(
        self,
        album_id: UUID,
        title: str,
        description: str | None,
        cover_url: str | None,
        is_private: bool,
        user_id: UUID,
        partner_id: UUID | None = None,
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
        user_id : UUID
            UUID пользователя-создателя альбома.
        partner_id : UUID | None, optional
            UUID партнера пользователя для проверки совместного доступа.
            По умолчанию None.

        Notes
        -----
        Внутренний метод `_insert_creator_in_query` добавляет условие
        WHERE для проверки прав создателя (пользователь или партнер).
        """
        query = (
            update(AlbumModel)
            .where(AlbumModel.id == album_id)
            .values(
                title=title,
                description=description,
                cover_url=cover_url,
                is_private=is_private,
            )
        )
        query = AlbumsRepository._insert_creator_in_query(query, user_id, partner_id)

        await self.session.execute(query)

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
