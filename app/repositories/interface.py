from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import Column, Select, Table, func, select
from sqlalchemy.ext.asyncio import AsyncConnection
from sqlalchemy.sql.elements import ColumnElement, UnaryExpression

from app.core.enums import SortOrder
from app.schemas.dto.base import BaseCreateDTO

CreateDTO = TypeVar("CreateDTO", bound=BaseCreateDTO)


class RepositoryInterface(ABC, Generic[CreateDTO]):
    """Интерфейс репозитория.

    Реализация паттерна Репозиторий. Является интерфейсом доступа к данным (DAO).

    Attributes
    ----------
    connection : AsyncConnection
        Объект асинхронного подключения запроса.
    """

    def __init__(self, connection: AsyncConnection):
        self.connection = connection

    @abstractmethod
    async def create(self, data: CreateDTO) -> None:
        """Создаёт новую запись.

        Parameters
        ----------
        data : CreateDTO
            Данные для создания записи.
        """
        ...

    @staticmethod
    def _build_count_query(
        table: Table, *where_clauses: ColumnElement[bool]
    ) -> Select[tuple[int]]:
        """Создаёт запрос подсчёта записей для пользователя и его партнёра.

        Parameters
        ----------
        table : Table
            Объект таблицы для подсчёта.
        where_clauses : ColumnElement[bool]
            Условие WHERE для фильтрации.

        Returns
        -------
        Select[tuple[int]]
            Запрос для подсчёта общего количества записей.
        """
        query = select(func.count()).select_from(table)

        if not where_clauses:
            return query

        return query.where(*where_clauses)

    @staticmethod
    def _build_order_clause(
        column: Column[Any], order: SortOrder
    ) -> UnaryExpression[Any]:
        """Создаёт выражение сортировки по переданной колонке.

        Parameters
        ----------
        column : Column[Any]
            Колонка модели, по которой выполняется сортировка.
        order : SortOrder
            Направление сортировки.

        Returns
        -------
        UnaryExpression[Any]
            Выражение сортировки по переданной колонке в заданном направлении.
        """
        return column.desc() if order == SortOrder.DESC else column.asc()


class SharedAccessMixin:
    """Миксин для фильтрации записей по создателю на уровне репозитория.

    Предназначен для наследования в репозиториях, работающих с таблицами,
    имеющими колонку `created_by`. Предоставляет вспомогательный метод
    для построения SQL-условий, ограничивающих выборку записями конкретного
    пользователя или его партнёра.
    """

    @staticmethod
    def _build_shared_clause(
        created_by_column: Column[UUID], user_id: UUID, partner_id: UUID | None = None
    ) -> ColumnElement[bool]:
        """Строит WHERE-условие для фильтрации записей по создателю.

        Parameters
        ----------
        created_by_column : Column[UUID]
            Колонка модели, содержащая UUID создателя записи.
        user_id : UUID
            UUID пользователя, чьи записи должны попасть в выборку.
        partner_id : UUID | None, optional
            UUID партнёра. Если передан, выборка расширяется до записей,
            созданных как пользователем, так и его партнёром.

        Returns
        -------
        ColumnElement[bool]
            SQLAlchemy-выражение, готовое к использованию в `.where()`.
        """
        if partner_id:
            return created_by_column.in_([user_id, partner_id])

        return created_by_column == user_id
