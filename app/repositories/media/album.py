import asyncio
from uuid import UUID

from sqlalchemy import and_, case, delete, func, insert, or_, select, text, update

from app.core.consts import DEFAULT_LIMIT, DEFAULT_OFFSET
from app.core.enums import SortOrder
from app.infra.postgres.tables.album_items import album_items_table
from app.infra.postgres.tables.albums import albums_table
from app.infra.postgres.tables.files import files_table
from app.infra.postgres.tables.users import users_table
from app.repositories.interface import (
    AccessContext,
    OwnedCreateMixin,
    OwnedDeleteMixin,
    OwnedReadMixin,
    OwnedRepositoryInterface,
    OwnedUpdateMixin,
)
from app.schemas.dto.album import (
    AlbumDTO,
    AlbumWithItemsDTO,
    CreateAlbumDTO,
    UpdateAlbumDTO,
)


class AlbumRepository(
    OwnedRepositoryInterface,
    OwnedReadMixin[AlbumDTO],
    OwnedCreateMixin[CreateAlbumDTO, AlbumDTO],
    OwnedUpdateMixin[UpdateAlbumDTO, AlbumDTO],
    OwnedDeleteMixin[AlbumDTO],
):
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

    _LIKE_ESCAPE_CHAR = "\\"
    """Символы экранирования для операции LIKE (и ILIKE)."""

    async def create(self, create_dto: CreateAlbumDTO, created_by: UUID) -> AlbumDTO:
        """Создаёт новый альбом с привязкой к владельцу.

        Parameters
        ----------
        create_dto : CreateFileDTO
            Данные для создания альбома.
        created_by : UUID
            Идентификатор пользователя, создающего альбом.
            Передаётся явно, так как извлекается из payload токена,
            а не из схемы запроса.

        Returns
        -------
        AlbumDTO
            Доменное DTO созданного альбома.
        """
        insert_cte = (
            insert(albums_table)
            .values(**create_dto.to_create_values(), created_by=created_by)
            .returning(albums_table)
            .cte("insert_cte")
        )
        result = await self.connection.execute(
            select(insert_cte, *self._creator_columns()).join(
                users_table, insert_cte.c.created_by == users_table.c.id
            )
        )

        return AlbumDTO.model_validate(result.mappings().one())

    async def get_all(
        self,
        access_ctx: AccessContext,
        *,
        offset: int = DEFAULT_OFFSET,
        limit: int = DEFAULT_LIMIT,
        sort_order: SortOrder = SortOrder.ASC,
    ) -> tuple[list[AlbumDTO], int]:
        """Возвращает постраничный список альбомов и их общее количество.

        Условие доступа и фильтры применяются на уровне запроса атомарно.
        Общее количество возвращается без учёта пагинации - для формирования
        метаданных ответа на клиенте.

        Parameters
        ----------
        access_ctx : AccessContext
            Контекст доступа с идентификаторами владельца и партнёра.
        offset : int, optional
            Количество пропускаемых записей, по умолчанию `DEFAULT_OFFSET`.
        limit : int, optional
            Максимальное количество возвращаемых записей, по умолчанию `DEFAULT_LIMIT`.
        sort_order : SortOrder, optional
            Направление сортировки по полю `created_at`,
            по умолчанию SortOrder.ASC.

        Returns
        -------
        tuple[list[AlbumDTO], int]
            Список DTO найденных альбомов и общее количество записей.
            Пустой список и 0, если альбомов нет или доступ ко всем из них запрещён.
        """
        where_clause = access_ctx.as_where_clause(albums_table.c.created_by)

        result, total = await asyncio.gather(
            self.connection.execute(
                select(albums_table, *self._creator_columns())
                .join(users_table, albums_table.c.created_by == users_table.c.id)
                .where(where_clause)
                .order_by(
                    self._build_order_clause(albums_table.c.created_at, sort_order)
                )
                .slice(offset, offset + limit)
            ),
            self.connection.scalar(self._build_count_query(albums_table, where_clause)),
        )

        return (
            [
                AlbumDTO.model_validate({**row, "creator": self._extract_creator(row)})
                for row in result.mappings().all()
            ],
            total or 0,
        )

    async def get_by_id(
        self, record_id: UUID, access_ctx: AccessContext
    ) -> AlbumDTO | None:
        """Получает DTO альбома по его UUID.

        Возвращает DTO альбома с указанным UUID
        и создателем (текущей пользователь или его партнёр).

        Parameters
        ----------
        record_id : UUID
            UUID пользовательского альбома.
        access_ctx : AccessContext
            Контекст доступа с идентификаторами владельца и партнёра.

        Returns
        -------
        AlbumDTO | None
            Доменное DTO записи альбома или None, если альбом не найден.
        """
        result = await self.connection.execute(
            select(albums_table, *self._creator_columns())
            .join(users_table, albums_table.c.created_by == users_table.c.id)
            .where(
                albums_table.c.id == record_id,
                access_ctx.as_where_clause(albums_table.c.created_by),
            )
        )

        if not (row := result.mappings().first()):
            return None

        return AlbumDTO.model_validate({**row, "creator": self._extract_creator(row)})

    async def search_by_trigram(
        self,
        access_ctx: AccessContext,
        search_query: str,
        threshold: float,
        *,
        offset: int = DEFAULT_OFFSET,
        limit: int = DEFAULT_LIMIT,
    ) -> tuple[list[AlbumDTO], int]:
        """Производит поиск альбомов по переданному запросу.

        Используется гибридный подход с поиском по полному вхождению (ILIKE)
        и по триграммам (% + GIN-индексы). Результат возвращается в порядке
        убывания сходства с запросом:
        - Первыми возвращаются результаты с полным совпадением;
        - Далее следуют результаты, отсортированные по значению функции `similarity`.

        Parameters
        ----------
        access_ctx : AccessContext
            Контекст доступа с идентификаторами владельца и партнёра.
        search_query : str
            Поисковый запрос, по которому производится поиск.
        threshold : float
            Порог сходства для поиска по триграммам.
        offset : int
            Смещение от начала списка (количество пропускаемых альбомов).
        limit : int
            Максимальное количество альбомов, которое необходимо вернуть.

        Returns
        -------
        tuple[list[AlbumDTO], int]
            Кортеж из списка найденных альбомов и их общего количества.
        """
        await self.connection.execute(
            text("SELECT set_limit(:threshold)"),
            {"threshold": threshold},
        )

        def escape_like(value: str, escape_char: str = self._LIKE_ESCAPE_CHAR) -> str:
            return (
                value.replace(escape_char, escape_char * 2)
                .replace("%", f"{escape_char}%")
                .replace("_", f"{escape_char}_")
            )

        ilike_pattern = f"%{escape_like(search_query)}%"

        ilikes = [
            albums_table.c.title.ilike(ilike_pattern, escape=self._LIKE_ESCAPE_CHAR),
            albums_table.c.description.ilike(
                ilike_pattern, escape=self._LIKE_ESCAPE_CHAR
            ),
        ]

        query = (
            select(albums_table, *self._creator_columns())
            .join(users_table, albums_table.c.created_by == users_table.c.id)
            .order_by(
                # полные вхождения в списке идут выше
                case((or_(*ilikes), 1.0), else_=0.0).desc(),
                func.greatest(
                    func.coalesce(
                        func.similarity(albums_table.c.title, search_query), 0.0
                    ),
                    func.coalesce(
                        func.similarity(albums_table.c.description, search_query), 0.0
                    ),
                ).desc(),
                albums_table.c.created_at,
            )
            .slice(offset, offset + limit)
        )

        where_clauses = [
            access_ctx.as_where_clause(albums_table.c.created_by),
            or_(
                # поиск полного вхождения
                *ilikes,
                # поиск по триграммам
                albums_table.c.title.op("%")(search_query),
                albums_table.c.description.op("%")(search_query),
            ),
        ]

        query = query.where(*where_clauses)
        count_query = self._build_count_query(albums_table, *where_clauses)

        result, total = await asyncio.gather(
            self.connection.execute(query),
            self.connection.scalar(count_query),
        )

        return [
            AlbumDTO.model_validate({**row, "creator": self._extract_creator(row)})
            for row in result.mappings().all()
        ], total or 0

    async def get_with_items(
        self,
        record_id: UUID,
        access_ctx: AccessContext,
        *,
        offset: int = DEFAULT_OFFSET,
        limit: int = DEFAULT_LIMIT,
    ) -> AlbumWithItemsDTO | None:
        """Получает DTO альбома с постраничным списком медиа-файлов.

        Параллельно выполняет три запроса: получение альбома с создателем,
        постраничную выборку медиа-файлов и подсчёт их общего количества.
        Файлы фильтруются по тому же контексту доступа, что и альбом.
        Если альбом не найден или недоступен - возвращает None.

        Parameters
        ----------
        record_id : UUID
            UUID пользовательского альбома.
        access_ctx : AccessContext
            Контекст доступа с идентификаторами владельца и партнёра.
            Применяется как к альбому, так и к его медиа-файлам.
        offset : int, optional
            Количество пропускаемых записей, по умолчанию `DEFAULT_OFFSET`.
        limit : int, optional
            Максимальное количество возвращаемых записей, по умолчанию `DEFAULT_LIMIT`.

        Returns
        -------
        AlbumWithItemsDTO | None
            DTO альбома с медиа-файлами, или None если альбом не найден.
        """
        # переиспользуется в запросе items и в count, чтобы total совпадал
        # с реальным количеством доступных файлов после фильтрации
        items_where_clause = and_(
            album_items_table.c.album_id == record_id,
            access_ctx.as_where_clause(files_table.c.created_by),
        )

        album_result, items_result, total = await asyncio.gather(
            # альбом с данными создателя
            self.connection.execute(
                select(albums_table, *self._creator_columns())
                .join(users_table, albums_table.c.created_by == users_table.c.id)
                .where(
                    albums_table.c.id == record_id,
                    access_ctx.as_where_clause(albums_table.c.created_by),
                )
            ),
            # постраничная выборка файлов альбома с данными их создателей
            self.connection.execute(
                select(files_table, *self._creator_columns())
                .join(users_table, files_table.c.created_by == users_table.c.id)
                .join(
                    album_items_table, files_table.c.id == album_items_table.c.file_id
                )
                .where(items_where_clause)
                .slice(offset, offset + limit)
            ),
            # общее количество доступных файлов (без учёта пагинации)
            self.connection.scalar(
                self._build_count_query(
                    album_items_table.join(
                        files_table, album_items_table.c.file_id == files_table.c.id
                    ),
                    items_where_clause,
                )
            ),
        )

        if not (album_row := album_result.mappings().first()):
            return None

        return AlbumWithItemsDTO.model_validate(
            {
                **album_row,
                "creator": self._extract_creator(album_row),
                "items": [
                    {**item_row, "creator": self._extract_creator(item_row)}
                    for item_row in items_result.mappings().all()
                ],
                "total": total or 0,
            }
        )

    async def update(
        self,
        record_id: UUID,
        update_dto: UpdateAlbumDTO,
        access_ctx: AccessContext,
    ) -> AlbumDTO | None:
        """Обновление атрибутов альбома в базе данных.

        Выполняет SQL-запрос UPDATE для изменения атрибутов альбома,
        фильтруя записи по идентификатору файла и правам доступа.

        Parameters
        ----------
        record_id : UUID
            UUID альбома к изменению.
        update_dto : UpdateAlbumDTO
            DTO с полями для обновления. Только явно переданные поля
            попадают в SET-часть запроса через `to_update_values()`.
        access_ctx : AccessContext
            Контекст доступа с идентификаторами владельца и партнёра.

        Returns
        -------
        AlbumDTO | None
            Доменное DTO альбома, если он обновлён, None - в ином случае.
        """
        update_cte = (
            update(albums_table)
            .where(
                albums_table.c.id == record_id,
                access_ctx.as_where_clause(albums_table.c.created_by),
            )
            .values(**update_dto.to_update_values())
            .returning(albums_table)
            .cte("update_cte")
        )
        result = await self.connection.execute(
            select(update_cte, *self._creator_columns()).join(
                users_table, update_cte.c.created_by == users_table.c.id
            )
        )

        if not (row := result.mappings().first()):
            return None

        return AlbumDTO.model_validate({**row, "creator": self._extract_creator(row)})

    async def delete(
        self, record_id: UUID, access_ctx: AccessContext
    ) -> AlbumDTO | None:
        """Удаляет запись о медиа альбоме из базы данных по его UUID.

        Parameters
        ----------
        record_id : UUID
            UUID альбома для удаления.
        access_ctx : AccessContext
            Контекст доступа с идентификаторами владельца и партнёра.

        Returns
        -------
        AlbumDTO | None
            Доменное DTO альбома, если он удалён, None - в ином случае.
        """
        delete_cte = (
            delete(albums_table)
            .where(
                albums_table.c.id == record_id,
                access_ctx.as_where_clause(albums_table.c.created_by),
            )
            .returning(albums_table)
            .cte("delete_cte")
        )
        result = await self.connection.execute(
            select(delete_cte, *self._creator_columns()).join(
                users_table, delete_cte.c.created_by == users_table.c.id
            )
        )

        if not (row := result.mappings().first()):
            return None

        return AlbumDTO.model_validate({**row, "creator": self._extract_creator(row)})

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
