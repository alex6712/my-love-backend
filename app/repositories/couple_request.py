import asyncio
from typing import Any, Literal

from sqlalchemy import (
    ColumnElement,
    FromClause,
    Label,
    RowMapping,
    Select,
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
from app.core.types import is_set
from app.infra.postgres.tables.couple_requests import couple_requests_table
from app.infra.postgres.tables.users import users_table
from app.repositories.interface import AccessContext, Creator, Reader, Updater
from app.schemas.dto.couple import (
    CoupleRequestDTO,
    CreateCoupleRequestDTO,
    FilterManyCoupleRequestsDTO,
    FilterOneCoupleRequestDTO,
    UpdateCoupleRequestDTO,
)

type PartnerPrefix = Literal["initiator", "recipient"]

initiators_table = users_table.alias("initiators")
recipients_table = users_table.alias("recipients")


class CoupleRequestRepository(
    Creator[CreateCoupleRequestDTO],
    Reader[FilterOneCoupleRequestDTO, FilterManyCoupleRequestsDTO, CoupleRequestDTO],
    Updater[
        FilterOneCoupleRequestDTO, FilterManyCoupleRequestsDTO, UpdateCoupleRequestDTO
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
            Префикс колонок - `"initiator"` или `"recipient"`.

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
            Префикс колонок - `"initiator"` или `"recipient"`.

        Returns
        -------
        dict[str, Any]
            Словарь с данными партнёра, готовый для вложенной валидации DTO.
        """
        return cls._extract_prefixed(
            row, prefix, ["id", "created_at", "username", "avatar_url", "is_active"]
        )

    async def create_one(self, create_dto: CreateCoupleRequestDTO) -> bool:
        """Создаёт новый запрос на создание пары.

        Parameters
        ----------
        create_dto : CreateCoupleRequestDTO
            DTO с данными для создания запроса.

        Returns
        -------
        bool
            True если запрос успешно создан.

        Raises
        ------
        CoupleRequestAlreadyExistsException
            Если между этими двумя пользователями уже существует
            запрос со статусом `PENDING` (нарушение `uq_couple_request_pending`).
        CoupleNotSelfException
            Если `initiator_id == recipient_id` (нарушение `ck_couple_not_self`).
        """
        try:
            result = await self.connection.execute(
                insert(couple_requests_table).values(**create_dto.to_create_values())
            )
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

        return result.rowcount == 1

    @classmethod
    def _filter_one_to_clauses(
        cls, filter_dto: FilterOneCoupleRequestDTO
    ) -> list[ColumnElement[bool]]:
        where_clauses = cls._get_where_clauses()

        if is_set(filter_dto.id):
            where_clauses.append(couple_requests_table.c.id == filter_dto.id)
        if is_set(filter_dto.initiator_id):
            where_clauses.append(
                couple_requests_table.c.initiator_id == filter_dto.initiator_id
            )
        if is_set(filter_dto.recipient_id):
            where_clauses.append(
                couple_requests_table.c.recipient_id == filter_dto.recipient_id
            )
        if is_set(filter_dto.status):
            where_clauses.append(couple_requests_table.c.status == filter_dto.status)

        return where_clauses

    @classmethod
    def _filter_many_to_clauses(
        cls, filter_dto: FilterManyCoupleRequestsDTO
    ) -> list[ColumnElement[bool]]:
        where_clauses = cls._get_where_clauses()

        if is_set(filter_dto.ids):
            where_clauses.append(couple_requests_table.c.id.in_(filter_dto.ids))
        if is_set(filter_dto.initiator_ids):
            where_clauses.append(
                couple_requests_table.c.initiator_id.in_(filter_dto.initiator_ids)
            )
        if is_set(filter_dto.recipient_ids):
            where_clauses.append(
                couple_requests_table.c.recipient_id.in_(filter_dto.recipient_ids)
            )
        if is_set(filter_dto.statuses):
            where_clauses.append(
                couple_requests_table.c.status.in_(filter_dto.statuses)
            )

        return where_clauses

    @classmethod
    def _build_read_statement(cls, *where_clauses: ColumnElement[bool]) -> Select[Any]:
        """Строит SELECT-запрос для чтения запроса с обоими участниками.

        Применяет фильтры из `filter_dto`, затем выполняет join `users_table`
        (алиасы `initiators_table` и `recipients_table`) для получения
        инициатора и реципиента.

        Используется в `read_one_for_update` и `read_many` во избежание
        дублирования логики построения запроса.

        Parameters
        ----------
        where_clauses : list[ColumnElement[bool]]
            Выражения для передачи в WHERE-часть запроса.

        Returns
        -------
        Select[Any]
            Готовый SELECT-запрос без исполнения.
        """
        return (
            select(
                couple_requests_table,
                *cls._partner_columns(initiators_table, "initiator"),
                *cls._partner_columns(recipients_table, "recipient"),
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
        )

    async def read_one_for_update(
        self, filter_dto: FilterOneCoupleRequestDTO, access_ctx: AccessContext
    ) -> CoupleRequestDTO | None:
        _ = access_ctx

        result = await self.connection.execute(
            self._build_read_statement(
                *self._filter_one_to_clauses(filter_dto)
            ).with_for_update()
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

    async def read_many(
        self,
        filter_dto: FilterManyCoupleRequestsDTO,
        access_ctx: AccessContext,
        *,
        offset: int = DEFAULT_OFFSET,
        limit: int = DEFAULT_LIMIT,
        sort_order: SortOrder = SortOrder.DESC,
    ) -> tuple[list[CoupleRequestDTO], int]:
        """Возвращает отфильтрованный список запросов на пару с общим их количеством.

        Выполняет два запроса параллельно: выборку страницы с JOIN-ами на обоих
        партнёров и подсчёт общего количества записей без учёта пагинации.

        Parameters
        ----------
        filter_dto : FilterCoupleRequestDTO
            Параметры фильтрации. Пустой DTO возвращает все записи.
        access_ctx : AccessContext
            Контекст доступа. Игнорируется.
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
            Список DTO запросов на текущей странице и общее количество записей,
            удовлетворяющих фильтру. Второй элемент равен `0`, если записей нет.

        Notes
        -----
        Каждая заявка содержит вложенные данные об инициаторе и получателе,
        извлекаемые через JOIN с таблицей пользователей (под алиасами
        `initiators_table` и `recipients_table`).
        """
        _ = access_ctx

        where_clauses = self._filter_many_to_clauses(filter_dto)

        result, total = await asyncio.gather(
            self.connection.execute(
                self._build_read_statement(*where_clauses)
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

    async def update_one(
        self,
        filter_dto: FilterOneCoupleRequestDTO,
        update_dto: UpdateCoupleRequestDTO,
        access_ctx: AccessContext,
    ) -> bool:
        """Обновляет запрос на создание пары по его идентификатору.

        Применяет переданные изменения к записи в `couple_requests`
        и возвращает подтверждение успешности операции.

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
        _ = access_ctx

        result = await self.connection.execute(
            update(couple_requests_table)
            .values(**update_dto.to_update_values())
            .where(*self._filter_one_to_clauses(filter_dto))
        )

        return result.rowcount == 1
