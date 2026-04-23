from typing import Any, Literal
from uuid import UUID

from sqlalchemy import (
    FromClause,
    Label,
    RowMapping,
    insert,
    literal,
    or_,
    select,
    update,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.core.exceptions.couple import CoupleAlreadyExistsException
from app.infra.postgres import get_constraint_name
from app.infra.postgres.tables.couple_members import couple_members_table
from app.infra.postgres.tables.couples import couples_table
from app.infra.postgres.tables.users import users_table
from app.models.couple import CoupleModel
from app.repositories.interface import (
    CreateMixin,
    ReadOneMixin,
    RepositoryInterfaceNew,
    UpdateMixin,
)
from app.schemas.dto.couple import CoupleDTO, CreateCoupleDTO, UpdateCoupleDTO
from app.schemas.dto.user import PartnerDTO

type PartnerPrefix = Literal["first_user", "second_user"]

first_users_table = users_table.alias("first_users")
second_users_table = users_table.alias("second_users")


class CoupleRepository(
    RepositoryInterfaceNew,
    CreateMixin[CreateCoupleDTO, CoupleDTO],
    ReadOneMixin[CoupleDTO],
    UpdateMixin[UpdateCoupleDTO, CoupleDTO],
):
    """Репозиторий пар между пользователями.

    Реализация паттерна Репозиторий. Является объектом доступа к данным (DAO).
    Реализует основные CRUD операции с парами пользователей.

    Methods
    -------
    add_couple(initiator_id, recipient_id)
        Регистрация пары между пользователями.
    get_couples_by_users_ids(first_user_id, second_user_id)
        Получение списка пар по UUID нескольких партнёров.
    get_partner_by_user_id(user_id)
        Получение информации о партнёре пользователя.
    update_couple_by_id(couple_id, patch_couple_dto, user_id)
        Обновление атрибутов пары между пользователями в базе данных.
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
        result = await self.connection.execute(
            select(
                insert_couple_cte,
                *self._partner_columns(first_users_table, "first_user"),
                *self._partner_columns(second_users_table, "second_user"),
            )
            # присоединяем таблицу couple_members по id пары для получения
            # пользователя в слоте 1
            .join(
                first_members_table := insert_members_cte.alias("first_members"),
                (insert_couple_cte.c.id == first_members_table.c.couple_id)
                & (first_members_table.c.slot == 1),
            )
            # получаем первого пользователя по его id
            .join(
                first_users_table,
                first_members_table.c.user_id == first_users_table.c.id,
            )
            # присоединяем таблицу couple_members по id пары для получения
            # пользователя в слоте 2
            .join(
                second_members_table := insert_members_cte.alias("second_members"),
                (insert_couple_cte.c.id == second_members_table.c.couple_id)
                & (second_members_table.c.slot == 2),
            )
            # получаем второго пользователя по его id
            .join(
                second_users_table,
                second_members_table.c.user_id == second_users_table.c.id,
            )
        )
        row = result.mappings().one()

        return CoupleDTO.model_validate(
            {
                **row,
                "first_user": self._extract_partner(row, "first_user"),
                "second_user": self._extract_partner(row, "second_user"),
            }
        )

    async def add_couple(self, user_low_id: UUID, user_high_id: UUID) -> None:
        """Создание записи о зарегистрированной паре между пользователями.

        Добавляет в базу данных запись о новой паре между пользователями.
        Уникальность и порядок UUID пользователей обеспечивается ограничениями
        базы данных.

        Parameters
        ----------
        user_low_id : UUID
            UUID пользователя-инициатора.
        user_high_id : UUID
            UUID пользователя-реципиента.
        """
        try:
            await self.session.execute(
                insert(CoupleModel).values(
                    user_low_id=user_low_id,
                    user_high_id=user_high_id,
                )
            )
        except IntegrityError as e:
            constraint = get_constraint_name(e)

            if constraint == "uq_couple_pair":
                raise CoupleAlreadyExistsException(
                    detail=f"Couple between {user_low_id} and {user_high_id} already exists!"
                ) from e

            raise

    async def get_couple_by_user_id(self, user_id: UUID) -> CoupleDTO | None:
        couple = await self.session.scalar(
            select(CoupleModel)
            .options(
                selectinload(CoupleModel.user_low),
                selectinload(CoupleModel.user_high),
            )
            .where(
                or_(
                    CoupleModel.user_low_id == user_id,
                    CoupleModel.user_high_id == user_id,
                )
            )
        )

        return CoupleDTO.model_validate(couple) if couple else None

    async def get_couples_by_partners_ids(self, *partners_ids: UUID) -> list[CoupleDTO]:
        """Получение списка пар по UUID нескольких партнёров.

        Parameters
        ----------
        *partner_ids : UUID
            Список UUID пользователей.

        Returns
        -------
        list[CoupleDTO]
            Список DTO пар, в которых состоит хотя бы один
            из переданных пользователей.
        """
        couples = await self.session.scalars(
            select(CoupleModel)
            .options(
                selectinload(CoupleModel.user_low),
                selectinload(CoupleModel.user_high),
            )
            .where(
                or_(
                    CoupleModel.user_low_id.in_(partners_ids),
                    CoupleModel.user_high_id.in_(partners_ids),
                )
            )
        )

        return [CoupleDTO.model_validate(couple) for couple in couples.all()]

    async def get_partner_by_user_id(self, user_id: UUID) -> PartnerDTO | None:
        """Получение информации о партнёре пользователя.

        Получает UUID пользователя, загружает информацию о паре,
        в которой этот пользователь состоит и возвращает DTO партнёра.

        Parameters
        ----------
        user_id : UUID
            UUID пользователя в системе.

        Returns
        -------
        PartnerDTO | None
            Сохранённая о партнёре пользователя информация:
            - PartnerDTO если партнёр найден;
            - None если партнёр не найден.
        """
        couple = await self.get_couple_by_user_id(user_id)

        if couple is None:
            return None

        return couple.user_low if couple.user_high.id == user_id else couple.user_high

    async def get_partner_id_by_user_id(self, user_id: UUID) -> UUID | None:
        """Получение UUID партнёра пользователя.

        Получает UUID пользователя, после чего ищет в БД запись
        о паре пользователей и возвращает UUID партнёра пользователя.

        Parameters
        ----------
        user_id : UUID
            UUID пользователя в системе.

        Returns
        -------
        UUID | None
            UUID партнёра пользователя или None, если пользователь не в паре.
        """
        couple = await self.session.scalar(
            select(CoupleModel).where(
                or_(
                    CoupleModel.user_low_id == user_id,
                    CoupleModel.user_high_id == user_id,
                ),
            )
        )

        if couple is None:
            return None

        return (
            couple.user_low_id
            if couple.user_high_id == user_id
            else couple.user_high_id
        )

    async def update_couple_by_id(
        self,
        couple_id: UUID,
        patch_couple_dto: UpdateCoupleDTO,
        user_id: UUID,
    ) -> bool:
        """Обновление атрибутов пары между пользователями в базе данных.

        Выполняет SQL-запрос UPDATE для изменения атрибутов пары,
        устанавливая переданные в patch DTO значения.

        Parameters
        ----------
        couple_id : UUID
            UUID пары к изменению.
        patch_couple_dto : UpdateCoupleDTO
            DTO с полями для обновления. Только явно переданные поля
            попадают в SET-часть запроса через `to_update_values()`.
        user_id : UUID
            UUID текущего пользователя.

        Returns
        -------
        bool
            True, если запись была обновлена, False - если пара
            не найдена или не прошла проверку прав доступа.
        """
        updated = await self.session.scalar(
            update(CoupleModel)
            .where(
                CoupleModel.id == couple_id,
                or_(
                    CoupleModel.user_low_id == user_id,
                    CoupleModel.user_high_id == user_id,
                ),
            )
            .values(**patch_couple_dto.to_update_values())
            .returning(CoupleModel.id)
        )

        return updated is not None
