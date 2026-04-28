from typing import Any, Literal, Sequence

from sqlalchemy import (
    FromClause,
    Label,
    RowMapping,
    Select,
    insert,
    literal,
    select,
    update,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.types import Uuid

from app.core.consts import DEFAULT_LIMIT, DEFAULT_OFFSET
from app.core.enums import SortOrder
from app.core.exceptions.couple import CoupleAlreadyExistsException
from app.core.types import is_set
from app.infra.postgres.tables.couple_members import couple_members_table
from app.infra.postgres.tables.couples import couples_table
from app.infra.postgres.tables.users import users_table
from app.repositories.interface import AccessContext, Creator, Reader, Updater
from app.schemas.dto.couple import (
    CoupleDTO,
    CreateCoupleDTO,
    FilterOneCoupleDTO,
    UpdateCoupleDTO,
)

type PartnerPrefix = Literal["first_user", "second_user"]

first_users_table = users_table.alias("first_users")
second_users_table = users_table.alias("second_users")


class CoupleRepository(
    Creator[CreateCoupleDTO],
    Reader[FilterOneCoupleDTO, Any, CoupleDTO],
    Updater[FilterOneCoupleDTO, Any, UpdateCoupleDTO],
):
    """Репозиторий пар между пользователями.

    Реализация паттерна Репозиторий. Является объектом доступа к данным (DAO).
    Реализует основные CRUD операции с парами пользователей.

    Methods
    -------
    create_one(create_dto)
        Создаёт пару и атомарно добавляет обоих участников.
    read_one(filter_dto, access_ctx)
        Возвращает пару, соответствующую переданным фильтрам.
    read_one_for_update(filter_dto, access_ctx)
        Возвращает пару с блокировкой строки для последующего изменения.
    update_one(filter_dto, update_dto, access_ctx)
        Обновляет пару по фильтрам.
    """

    @classmethod
    def _partner_columns(
        cls, alias: FromClause, prefix: PartnerPrefix
    ) -> list[Label[Any]]:
        """Именованные колонки пользователя для SELECT.

        Parameters
        ----------
        alias : FromClause
            Псевдоним таблицы users.
        prefix : PartnerPrefix
            Префикс колонок - `"first_user"` или `"second_user"`.

        Returns
        -------
        list[Label[Any]]
            Список лейблированных колонок users_table.
        """
        return cls._label_columns(
            [
                alias.c.id,
                alias.c.created_at,
                alias.c.username,
                alias.c.avatar_url,
                alias.c.is_active,
            ],
            prefix,
        )

    @classmethod
    def _extract_partner(cls, row: RowMapping, prefix: PartnerPrefix) -> dict[str, Any]:
        """Извлекает данные партнёра из плоской строки JOIN-результата.

        Parameters
        ----------
        row : RowMapping
            Плоская строка результата запроса с лейблированными
            колонками пользователя.
        prefix : PartnerPrefix
            Префикс колонок - `"first_user"` или `"second_user"`.

        Returns
        -------
        dict[str, Any]
            Словарь с данными партнёра, готовый для вложенной валидации DTO.
        """
        return cls._extract_prefixed(
            row, prefix, ["id", "created_at", "username", "avatar_url", "is_active"]
        )

    async def create_one(self, create_dto: CreateCoupleDTO) -> bool:
        """Создаёт пару и атомарно добавляет обоих участников.

        Выполняет три операции в рамках одного запроса через цепочку CTE:

        1. `insert_couple_cte` - вставляет запись в `couples`;
        2. `insert_members_cte` - вставляет двух участников в
        `couple_members` через `INSERT ... FROM SELECT`,
        назначая им слоты `1` и `2`.

        Parameters
        ----------
        create_dto : CreateCoupleDTO
            DTO с данными для создания пары.

        Returns
        -------
        bool
            True если пара и оба участника успешно созданы.

        Raises
        ------
        CoupleAlreadyExistsException
            Если один из пользователей уже состоит в паре.
        """
        insert_couple_cte = (
            insert(couples_table)
            .values(relationship_started_on=create_dto.relationship_started_on)
            .returning(couples_table.c.id)
            .cte("insert_couple_cte")
        )
        member_rows = select(
            insert_couple_cte.c.id.label("couple_id"),
            literal(create_dto.first_user_id, type_=Uuid(as_uuid=True)).label(
                "user_id"
            ),
            literal(1).label("slot"),
        ).union_all(
            select(
                insert_couple_cte.c.id.label("couple_id"),
                literal(create_dto.second_user_id, type_=Uuid(as_uuid=True)).label(
                    "user_id"
                ),
                literal(2).label("slot"),
            )
        )

        try:
            result = await self.connection.execute(
                insert(couple_members_table).from_select(
                    ["couple_id", "user_id", "slot"], member_rows
                )
            )
        except IntegrityError as e:
            if "uq_one_couple_per_user" in str(e):
                raise CoupleAlreadyExistsException(
                    detail=f"User {create_dto.first_user_id} or {create_dto.second_user_id} is already in couple!",
                ) from e

            raise

        return result.rowcount == 2

    async def create_many(self, create_dtos: Sequence[CreateCoupleDTO]) -> int:
        """Не поддерживается для данной сущности.

        Не предусмотрено создание множества пар за одну транзакцию,
        т.к. один пользователь не может состоять более чем в одной паре.
        """

        raise NotImplementedError(
            "Method 'create_many' is not implemented in CoupleRepository"
        )

    @classmethod
    def _build_read_statement(cls, filter_dto: FilterOneCoupleDTO) -> Select[Any]:
        """Строит SELECT-запрос для чтения пары с обоими участниками.

        Применяет фильтры из `filter_dto`, затем выполняет двойной
        self-join `couple_members` (алиасы `m1` и `m2`) для раздельного
        получения первого и второго участников по слотам, после чего
        присоединяет `users` для каждого из них.

        Используется в `read_one` и `read_one_for_update` во избежание
        дублирования логики построения запроса.

        Parameters
        ----------
        filter_dto : FilterOneCoupleDTO
            DTO с полями фильтрации. Поддерживает `couple_id` и `user_id`.

        Returns
        -------
        Select[Any]
            Готовый SELECT-запрос без исполнения.
        """
        where_clauses = cls._get_where_clauses()
        if is_set(filter_dto.couple_id):
            where_clauses.append(
                couple_members_table.c.couple_id == filter_dto.couple_id
            )
        if is_set(filter_dto.user_id):
            where_clauses.append(couple_members_table.c.user_id == filter_dto.user_id)

        return (
            select(
                couples_table,
                *cls._partner_columns(first_users_table, "first_user"),
                *cls._partner_columns(second_users_table, "second_user"),
            )
            .select_from(couple_members_table)
            .join(
                couples_table,
                couples_table.c.id == couple_members_table.c.couple_id,
            )
            .join(
                m1 := couple_members_table.alias("m1"),
                (m1.c.couple_id == couples_table.c.id) & (m1.c.slot == 1),
            )
            .join(first_users_table, first_users_table.c.id == m1.c.user_id)
            .join(
                m2 := couple_members_table.alias("m2"),
                (m2.c.couple_id == couples_table.c.id) & (m2.c.slot == 2),
            )
            .join(second_users_table, second_users_table.c.id == m2.c.user_id)
            .where(*where_clauses)
        )

    async def read_one(
        self, filter_dto: FilterOneCoupleDTO, access_ctx: AccessContext
    ) -> CoupleDTO | None:
        """Возвращает пару, соответствующую переданным фильтрам.

        Строит запрос через двойной self-join `couple_members`
        (алиасы `m1` и `m2`) для раздельного получения первого
        и второго участников, затем присоединяет `users` для каждого из них.

        Parameters
        ----------
        filter_dto : FilterOneCoupleDTO
            DTO с полями фильтрации.
        access_ctx : AccessContext
            Контекст доступа. Игнорируется.

        Returns
        -------
        CoupleDTO | None
            Найденная пара с вложенными DTO обоих участников или None,
            если ни одна пара не соответствует фильтрам.
        """
        _ = access_ctx

        result = await self.connection.execute(self._build_read_statement(filter_dto))

        if not (row := result.mappings().first()):
            return None

        return CoupleDTO.model_validate(
            {
                **row,
                "first_user": self._extract_partner(row, "first_user"),
                "second_user": self._extract_partner(row, "second_user"),
            }
        )

    async def read_one_for_update(
        self, filter_dto: FilterOneCoupleDTO, access_ctx: AccessContext
    ) -> CoupleDTO | None:
        """Возвращает пару с блокировкой строки для последующего изменения.

        Строит запрос через двойной self-join `couple_members`
        (алиасы `m1` и `m2`) для раздельного получения первого
        и второго участников, затем присоединяет `users` для
        каждого из них.

        Устанавливает `SELECT ... FOR UPDATE` - строка блокируется
        до завершения транзакции. Должен вызываться внутри транзакции.

        Parameters
        ----------
        filter_dto : FilterOneCoupleDTO
            DTO с полями фильтрации.
        access_ctx : AccessContext
            Контекст доступа. Игнорируется.

        Returns
        -------
        CoupleDTO | None
            Найденная пара с вложенными DTO обоих участников или None,
            если ни одна пара не соответствует фильтрам.
        """
        _ = access_ctx

        result = await self.connection.execute(
            self._build_read_statement(filter_dto).with_for_update()
        )

        if not (row := result.mappings().first()):
            return None

        return CoupleDTO.model_validate(
            {
                **row,
                "first_user": self._extract_partner(row, "first_user"),
                "second_user": self._extract_partner(row, "second_user"),
            }
        )

    async def read_many(
        self,
        filter_dto: Any,
        access_ctx: AccessContext,
        *,
        offset: int = DEFAULT_OFFSET,
        limit: int = DEFAULT_LIMIT,
        sort_order: SortOrder = SortOrder.DESC,
    ) -> tuple[list[CoupleDTO], int]:
        """Не поддерживается для данной сущности.

        Не предусмотрено чтение множества пар за одну транзакцию,
        т.к. один пользователь не может состоять более чем в одной паре.
        """

        raise NotImplementedError(
            "Method 'read_many' is not implemented in CoupleRepository"
        )

    async def update_one(
        self,
        filter_dto: FilterOneCoupleDTO,
        update_dto: UpdateCoupleDTO,
        access_ctx: AccessContext,
    ) -> bool:
        """Обновляет пару по фильтрам.

        Если запись не найдена - возвращает `False`, делегируя
        решение об ошибке вышестоящему слою.

        Parameters
        ----------
        filter_dto : FilterOneCoupleDTO
            DTO с полями фильтрации для поиска обновляемой записи.
        update_dto : UpdateCoupleDTO
            DTO с обновляемыми полями.
        access_ctx : AccessContext
            Контекст доступа. Игнорируется.

        Returns
        -------
        bool
            True если пара найдена и успешно обновлена.
        """
        _ = access_ctx

        where_clauses = self._get_where_clauses()
        if is_set(filter_dto.couple_id):
            where_clauses.append(couples_table.c.id == filter_dto.couple_id)
        if is_set(filter_dto.user_id):
            where_clauses.append(
                couples_table.c.id.in_(
                    select(couple_members_table.c.couple_id).where(
                        couple_members_table.c.user_id == filter_dto.user_id
                    )
                )
            )

        result = await self.connection.execute(
            update(couples_table)
            .values(**update_dto.to_update_values())
            .where(*where_clauses)
        )

        return result.rowcount == 1

    async def update_many(
        self, filter_dto: Any, update_dto: UpdateCoupleDTO, access_ctx: AccessContext
    ) -> int:
        """Не поддерживается для данной сущности.

        Не предусмотрено обновление множества пар за одну транзакцию,
        т.к. один пользователь не может состоять более чем в одной паре.
        """

        raise NotImplementedError(
            "Method 'update_many' is not implemented in CoupleRepository"
        )
