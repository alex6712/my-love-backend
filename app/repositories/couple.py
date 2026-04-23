from typing import Any, Literal

from sqlalchemy import FromClause, Label, RowMapping, insert, literal, select
from sqlalchemy.exc import IntegrityError

from app.core.exceptions.couple import CoupleAlreadyExistsException
from app.infra.postgres import get_constraint_name
from app.infra.postgres.tables.couple_members import couple_members_table
from app.infra.postgres.tables.couples import couples_table
from app.infra.postgres.tables.users import users_table
from app.repositories.interface import (
    CreateMixin,
    FilteredReadOneMixin,
    RepositoryInterfaceNew,
)
from app.schemas.dto.couple import (
    CoupleDTO,
    CreateCoupleDTO,
    FilterCoupleDTO,
)

type PartnerPrefix = Literal["first_user", "second_user"]

first_users_table = users_table.alias("first_users")
second_users_table = users_table.alias("second_users")


class CoupleRepository(
    RepositoryInterfaceNew,
    CreateMixin[CreateCoupleDTO, CoupleDTO],
    FilteredReadOneMixin[FilterCoupleDTO, CoupleDTO],
):
    """Репозиторий пар между пользователями.

    Реализация паттерна Репозиторий. Является объектом доступа к данным (DAO).
    Реализует основные CRUD операции с парами пользователей.

    Methods
    -------
    create(create_dto)
        Создаёт пару и атомарно добавляет обоих участников.
    get_one_filtered(filter_dto)
        Возвращает пару, соответствующую переданным фильтрам.
    """

    @staticmethod
    def _partner_columns(alias: FromClause, prefix: PartnerPrefix) -> list[Label[Any]]:
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
        return [
            alias.c.id.label(f"_{prefix}_id"),
            alias.c.created_at.label(f"_{prefix}_created_at"),
            alias.c.username.label(f"_{prefix}_username"),
            alias.c.avatar_url.label(f"_{prefix}_avatar_url"),
            alias.c.is_active.label(f"_{prefix}_is_active"),
        ]

    @staticmethod
    def _extract_partner(row: RowMapping, prefix: PartnerPrefix) -> dict[str, Any]:
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
        return {
            "id": row[f"_{prefix}_id"],
            "username": row[f"_{prefix}_username"],
            "avatar_url": row[f"_{prefix}_avatar_url"],
            "is_active": row[f"_{prefix}_is_active"],
            "created_at": row[f"_{prefix}_created_at"],
            "updated_at": row[f"_{prefix}_updated_at"],
        }

    async def create(self, create_dto: CreateCoupleDTO) -> CoupleDTO:
        """Создаёт пару и атомарно добавляет обоих участников.

        Выполняет три операции в рамках одного запроса через цепочку CTE:

        1. `insert_couple_cte` - вставляет запись в `couples`;
        2. `insert_members_cte` - вставляет двух участников в
        `couple_members` через `INSERT ... FROM SELECT`,
        назначая им слоты `1` и `2`;
        3. Итоговый `SELECT` - возвращает пару с данными обоих
        участников через JOIN с `users`.

        Parameters
        ----------
        create_dto : CreateCoupleDTO
            DTO с данными для создания пары.

        Returns
        -------
        CoupleDTO
            Созданная пара с вложенными DTO первого и второго участников.
        """
        insert_couple_cte = (
            insert(couples_table)
            .values(**create_dto.to_create_values())
            .returning(couples_table)
            .cte("insert_couple_cte")
        )
        member_rows = select(
            insert_couple_cte.c.id.label("couple_id"),
            literal(create_dto.first_user_id).label("user_id"),
            literal(1).label("slot"),
        ).union_all(
            select(
                insert_couple_cte.c.id.label("couple_id"),
                literal(create_dto.second_user_id).label("user_id"),
                literal(2).label("slot"),
            )
        )
        insert_members_cte = (
            insert(couple_members_table)
            .from_select(["couple_id", "user_id", "slot"], member_rows)
            .returning(couple_members_table)
            .cte("insert_members_cte")
        )

        try:
            result = await self.connection.execute(
                select(
                    insert_couple_cte,
                    *self._partner_columns(first_users_table, "first_user"),
                    *self._partner_columns(second_users_table, "second_user"),
                )
                # получаем первого пользователя
                .join(
                    m1 := insert_members_cte.alias("m1"),
                    (m1.c.couple_id == insert_couple_cte.c.id) & (m1.c.slot == 1),
                )
                .join(first_users_table, first_users_table.c.id == m1.c.user_id)
                # получаем второго пользователя
                .join(
                    m2 := insert_members_cte.alias("m2"),
                    (m2.c.couple_id == insert_couple_cte.c.id) & (m2.c.slot == 2),
                )
                .join(second_users_table, second_users_table.c.id == m2.c.user_id)
            )
            row = result.mappings().one()
        except IntegrityError as e:
            constraint_name = get_constraint_name(e)

            if constraint_name == "uq_one_couple_per_user":
                raise CoupleAlreadyExistsException(
                    detail=f"User {create_dto.first_user_id} or {create_dto.second_user_id} is already in couple!",
                ) from e

            raise

        return CoupleDTO.model_validate(
            {
                **row,
                "first_user": self._extract_partner(row, "first_user"),
                "second_user": self._extract_partner(row, "second_user"),
            }
        )

    async def get_one_filtered(self, filter_dto: FilterCoupleDTO) -> CoupleDTO | None:
        """Возвращает пару, соответствующую переданным фильтрам.

        Строит запрос через двойной self-join `couple_members`
        (алиасы `m1` и `m2`) для раздельного получения первого
        и второго участников, затем присоединяет `users` для
        каждого из них.

        Parameters
        ----------
        filter_dto : FilterCoupleDTO
            DTO с полями фильтрации. Пустой DTO вернёт первую
            попавшуюся пару.

        Returns
        -------
        CoupleDTO | None
            Найденная пара с вложенными DTO обоих участников или None,
            если ни одна пара не соответствует фильтрам.
        """
        result = await self.connection.execute(
            select(
                couples_table,
                *self._partner_columns(first_users_table, "first_user"),
                *self._partner_columns(second_users_table, "second_user"),
            )
            .select_from(couple_members_table)
            .join(
                couples_table,
                couples_table.c.id == couple_members_table.c.couple_id,
            )
            # первый участник
            .join(
                m1 := couple_members_table.alias("m1"),
                (m1.c.couple_id == couples_table.c.id) & (m1.c.slot == 1),
            )
            .join(first_users_table, first_users_table.c.id == m1.c.user_id)
            # второй участник
            .join(
                m2 := couple_members_table.alias("m2"),
                (m2.c.couple_id == couples_table.c.id) & (m2.c.slot == 2),
            )
            .join(second_users_table, second_users_table.c.id == m2.c.user_id)
            .where(
                *[
                    getattr(couple_members_table.c, field) == value
                    for field, value in filter_dto.to_filter_values().items()
                ]
            )
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
