from abc import ABC
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped
from sqlalchemy.sql.elements import ColumnElement


class RepositoryInterface(ABC):
    """Интерфейс репозитория.

    Реализация паттерна Репозиторий. Является интерфейсом доступа к данным (DAO).

    Attributes
    ----------
    session : AsyncSession
        Объект асинхронной сессии запроса.
    """

    def __init__(self, session: AsyncSession):
        self.session: AsyncSession = session

    @staticmethod
    def _build_count_query(
        model_class: type[Any], *where_clauses: ColumnElement[bool]
    ) -> Select[tuple[int]]:
        """Создаёт запрос подсчёта записей для пользователя и его партнёра.

        Parameters
        ----------
        model_class : Any
            Класс модели для подсчёта.
        where_clauses : ColumnElement[bool]
            Условие WHERE для фильтрации.

        Returns
        -------
        Select[tuple[int]]
            Запрос для подсчёта общего количества записей.
        """
        query = select(func.count()).select_from(model_class)

        if not where_clauses:
            return query

        return query.where(*where_clauses)


class HasCreatedBy(Protocol):
    """Протокол для типизации SQLAlchemy моделей с атрибутом created_by.

    Определяет структурный интерфейс для моделей, которые содержат информацию
    о создателе записи в виде колонки `created_by` типа `UUID`.

    Протокол использует механизм "утиной типизации" и позволяет
    использовать любой класс, имеющий атрибут `created_by: Mapped[UUID]`,
    в качестве аргумента для методов, ожидающих такие модели.

    Notes
    -----
    Это runtime-проверяемый протокол, что позволяет использовать `isinstance()`
    для проверки соответствия классов протоколу во время выполнения программы.
    """

    created_by: Mapped[UUID]


class SharedResourceRepository(RepositoryInterface):
    """Базовый репозиторий для работы с ресурсами, доступными нескольким пользователям.

    Предоставляет общие методы для построения SQL-условий фильтрации по полю `created_by`,
    позволяя ограничивать доступ к ресурсам на уровне записей в зависимости от
    пользователя и его партнёра.

    Этот репозиторий предназначен для наследования и использования в репозиториях,
    работающих с моделями, которые соответствуют протоколу `HasCreatedBy`.

    Methods
    -------
    _build_shared_clause(model_class, user_id, partner_id=None)
        Строит условия WHERE для фильтрации записей по создателю.

    Inherits
    --------
    RepositoryInterface : abc.ABC
        Базовый интерфейс репозитория с общими методами доступа к данным.
    """

    @staticmethod
    def _build_shared_clause(
        model_class: type[HasCreatedBy], user_id: UUID, partner_id: UUID | None = None
    ) -> ColumnElement[bool]:
        """Создаёт условие WHERE для фильтрации записей по создателю и партнёру.

        Генерирует SQLAlchemy выражение для ограничения выборки записей модели
        только теми, которые были созданы указанным пользователем или его партнёром.

        Parameters
        ----------
        model_class : type[HasCreatedBy]
            Класс SQLAlchemy модели, соответствующий протоколу `HasCreatedBy`.
        user_id : UUID
            UUID пользователя, для которого выполняется фильтрация.
        partner_id : UUID | None, optional
            UUID партнёра пользователя. Если передан, фильтрация будет включать
            записи, созданные как пользователем, так и его партнёром.

        Returns
        -------
        ColumnElement[bool]
            Объект SQLAlchemy выражения для использования в WHERE-условиях.
        """
        if partner_id:
            return model_class.created_by.in_([user_id, partner_id])

        return model_class.created_by == user_id
