import asyncio
from typing import Any, Literal

from sqlalchemy import (
    FromClause,
    Label,
    RowMapping,
    insert,
    select,
    update,
)
from sqlalchemy.exc import IntegrityError

from app.core.consts import DEFAULT_LIMIT, DEFAULT_OFFSET
from app.core.enums import SortOrder
from app.core.exceptions.couple import (
    CoupleNotSelfException,
    CoupleRequestAlreadyExistsException,
)
from app.infra.postgres.tables.couple_requests import couple_requests_table
from app.infra.postgres.tables.users import users_table
from app.repositories.interface import (
    CreateMixin,
    FilteredReadMixin,
    FilteredUpdateMixin,
    RepositoryInterface,
)
from app.schemas.dto.couple import (
    CoupleRequestDTO,
    CreateCoupleRequestDTO,
    FilterCoupleRequestDTO,
    UpdateCoupleRequestDTO,
)

type PartnerPrefix = Literal["initiator", "recipient"]

initiators_table = users_table.alias("initiators")
recipients_table = users_table.alias("recipients")


class CoupleRequestRepository(
    RepositoryInterface,
    CreateMixin[CreateCoupleRequestDTO, CoupleRequestDTO],
    FilteredReadMixin[FilterCoupleRequestDTO, CoupleRequestDTO],
    FilteredUpdateMixin[
        FilterCoupleRequestDTO, UpdateCoupleRequestDTO, CoupleRequestDTO
    ],
):
    """Репозиторий запросов на создание пар между пользователями.

    Реализация паттерна Репозиторий. Является объектом доступа к данным (DAO).
    Реализует основные CRUD операции с парами пользователей.

    Attributes
    ----------
    session : AsyncSession
        Объект асинхронной сессии запроса.

    Methods
    -------
    add_couple_request(initiator_id, recipient_id)
        Создание запроса на регистрацию пары между пользователями.
    get_pending_requests_for_recipient(recipient_id)
        Получение входящих запросов для пользователя.
    update_request_status_by_id_and_recipient_id(couple_request_id, recipient_id, new_status)
        Обновление статуса входящего запроса на создание пары.
    """

    @staticmethod
    def _partner_columns(alias: FromClause, prefix: PartnerPrefix) -> list[Label[Any]]:
        """Именованные колонки пользователя для SELECT.

        Используется префикс `_`, чтобы не конфликтовать с
        `initiator_id` / `recipient_id` из `couple_requests_table`.

        Parameters
        ----------
        alias : FromClause
            Псевдоним таблицы users.
        prefix : PartnerPrefix
            Префикс колонок - `"initiator"` или `"recipient"`.

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
            Префикс колонок - `"initiator"` или `"recipient"`.

        Returns
        -------
        dict[str, Any]
            Словарь с данными партнёра, готовый для вложенной валидации DTO.
        """
        return {
            "id": row[f"_{prefix}_id"],
            "created_at": row[f"_{prefix}_created_at"],
            "username": row[f"_{prefix}_username"],
            "avatar_url": row[f"_{prefix}_avatar_url"],
            "is_active": row[f"_{prefix}_is_active"],
        }

    async def create(self, create_dto: CreateCoupleRequestDTO) -> CoupleRequestDTO:
        """Создаёт новый запрос на создание пары.

        Вставляет запись в `couple_requests` и сразу возвращает её
        вместе с данными обоих участников через JOIN с `users`.

        Parameters
        ----------
        create_dto : CreateCoupleRequestDTO
            DTO с данными для создания запроса.

        Returns
        -------
        CoupleRequestDTO
            Созданный запрос на пару с вложенными DTO инициатора и реципиента.

        Raises
        ------
        CoupleRequestAlreadyExistsException
            Если между этими двумя пользователями уже существует
            запрос со статусом `PENDING` (нарушение `uq_couple_request_pending`).
        CoupleNotSelfException
            Если `initiator_id == recipient_id` (нарушение `ck_couple_not_self`).
        """
        try:
            insert_cte = (
                insert(couple_requests_table)
                .values(**create_dto.to_create_values())
                .returning(couple_requests_table)
                .cte("insert_cte")
            )
            result = await self.connection.execute(
                select(
                    insert_cte,
                    *self._partner_columns(initiators_table, "initiator"),
                    *self._partner_columns(recipients_table, "recipient"),
                )
                .join(
                    initiators_table, initiators_table.c.id == insert_cte.c.initiator_id
                )
                .join(
                    recipients_table, recipients_table.c.id == insert_cte.c.recipient_id
                )
            )
            row = result.mappings().one()
        except IntegrityError as e:
            if "uq_couple_request_pending" in str(e):
                raise CoupleRequestAlreadyExistsException(
                    detail=f"Pending request from {create_dto.initiator_id} to {create_dto.recipient_id} already exists!"
                ) from e
            elif "ck_couple_not_self" in str(e):
                raise CoupleNotSelfException(
                    detail="Cannot register couple with yourself!"
                ) from e

            raise

        return CoupleRequestDTO.model_validate(
            {
                **row,
                "initiator": self._extract_partner(row, "initiator"),
                "recipient": self._extract_partner(row, "recipient"),
            }
        )

    async def get_filtered(
        self,
        filter_dto: FilterCoupleRequestDTO,
        *,
        offset: int = DEFAULT_OFFSET,
        limit: int = DEFAULT_LIMIT,
        sort_order: SortOrder = SortOrder.DESC,
    ) -> tuple[list[CoupleRequestDTO], int]:
        """Возвращает отфильтрованный список заявок на пару с общим их количеством.

        Выполняет два запроса параллельно: выборку страницы с JOIN-ами на обоих
        партнёров и подсчёт общего количества записей без учёта пагинации.

        Parameters
        ----------
        filter_dto : FilterCoupleRequestDTO
            Параметры фильтрации. Пустой DTO возвращает все записи.
        offset : int, optional
            Количество пропускаемых записей, по умолчанию `DEFAULT_OFFSET`.
        limit : int, optional
            Максимальное количество возвращаемых записей, по умолчанию `DEFAULT_LIMIT`.
        sort_order : SortOrder, optional
            Направление сортировки по полю `created_at`,
            по умолчанию `SortOrder.DESC`.

        Returns
        -------
        tuple[list[CoupleRequestDTO], int]
            Список DTO заявок на текущей странице и общее количество записей,
            удовлетворяющих фильтру. Второй элемент равен `0`, если записей нет.

        Notes
        -----
        Каждая заявка содержит вложенные данные об инициаторе и получателе,
        извлекаемые через JOIN с таблицей пользователей (под алиасами
        `initiators_table` и `recipients_table`).
        """
        where_clauses = [
            getattr(couple_requests_table.c, field) == value
            for field, value in filter_dto.to_filter_values().items()
        ]

        result, total = await asyncio.gather(
            self.connection.execute(
                select(
                    couple_requests_table,
                    *self._partner_columns(initiators_table, "initiator"),
                    *self._partner_columns(recipients_table, "recipient"),
                )
                .join(
                    initiators_table,
                    initiators_table.c.id == couple_requests_table.c.initiator_id,
                )
                .join(
                    recipients_table,
                    recipients_table.c.id == couple_requests_table.c.recipient_id,
                )
                .where(*where_clauses)
                .order_by(
                    self._build_order_clause(
                        couple_requests_table.c.created_at, sort_order
                    )
                )
                .slice(offset, offset + limit)
            ),
            self.connection.scalar(
                self._build_count_query(couple_requests_table, *where_clauses)
            ),
        )

        return (
            [
                CoupleRequestDTO.model_validate(
                    {
                        **row,
                        "initiator": self._extract_partner(row, "initiator"),
                        "recipient": self._extract_partner(row, "recipient"),
                    }
                )
                for row in result.mappings().all()
            ],
            total or 0,
        )

    async def update_filtered(
        self, filter_dto: FilterCoupleRequestDTO, update_dto: UpdateCoupleRequestDTO
    ) -> CoupleRequestDTO | None:
        """Обновляет запрос на создание пары по его идентификатору.

        Применяет переданные изменения к записи в `couple_requests`
        и возвращает актуальное состояние с данными обоих участников.

        Parameters
        ----------
        record_id : UUID
            Идентификатор обновляемого запроса.
        update_dto : UpdateCoupleRequestDTO
            DTO с обновляемыми полями.

        Returns
        -------
        CoupleRequestDTO | None
            Обновлённый запрос на пару с вложенными DTO инициатора и реципиента
            или None, если запрос не найден.
        """
        where_clauses = [
            getattr(couple_requests_table.c, field) == value
            for field, value in filter_dto.to_filter_values().items()
        ]

        update_cte = (
            update(couple_requests_table)
            .values(**update_dto.to_update_values())
            .where(*where_clauses)
            .returning(couple_requests_table)
            .cte("update_cte")
        )
        result = await self.connection.execute(
            select(
                couple_requests_table,
                *self._partner_columns(initiators_table, "initiator"),
                *self._partner_columns(recipients_table, "recipient"),
            )
            .join(initiators_table, initiators_table.c.id == update_cte.c.initiator_id)
            .join(recipients_table, recipients_table.c.id == update_cte.c.recipient_id)
        )

        if not (row := result.mappings().first()):
            return None

        return CoupleRequestDTO.model_validate(
            {
                **row,
                "initiator": self._extract_partner(row, "initiator"),
                "recipient": self._extract_partner(row, "recipient"),
            }
        )
