from abc import ABC, abstractmethod
from typing import Any, Generic, Protocol, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, Label, RowMapping, Select, Table, func, select
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession
from sqlalchemy.orm import Mapped
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.sql.elements import ColumnElement, UnaryExpression

from app.core.consts import DEFAULT_LIMIT, DEFAULT_OFFSET
from app.core.enums import SortOrder
from app.infra.postgres.tables.users import users_table
from app.schemas.dto.base import (
    BaseCreateDTO,
    BaseFilterDTO,
    BaseSQLCoreDTO,
    BaseUpdateDTO,
)

EntityDTO = TypeVar("EntityDTO", bound=BaseSQLCoreDTO)
FilterDTO = TypeVar("FilterDTO", bound=BaseFilterDTO)
CreateDTO = TypeVar("CreateDTO", bound=BaseCreateDTO)
UpdateDTO = TypeVar("UpdateDTO", bound=BaseUpdateDTO)


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

    @staticmethod
    def _build_order_clause(
        column: InstrumentedAttribute[Any], order: SortOrder
    ) -> UnaryExpression[Any]:
        """Создаёт выражение сортировки по переданной колонке.

        Parameters
        ----------
        column : InstrumentedAttribute[Any]
            Колонка модели, по которой выполняется сортировка.
        order : SortOrder
            Направление сортировки.

        Returns
        -------
        UnaryExpression[Any]
            Выражение сортировки по переданной колонке в заданном направлении.
        """
        return column.desc() if order == SortOrder.DESC else column.asc()


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


class AccessContext(BaseModel):
    """Контекст доступа к записи с ограниченной видимостью.

    Используется для атомарной проверки прав владения при мутациях
    и фильтрации выборок. Условие доступа включается непосредственно
    в WHERE-clause запроса, исключая TOCTOU.

    Attributes
    ----------
    user_id : UUID
        Идентификатор пользователя, выполняющего запрос.
    partner_id : UUID | None
        Идентификатор партнёра пользователя. Если передан,
        доступ распространяется и на его записи.
    """

    user_id: UUID
    partner_id: UUID | None = None

    def as_where_clause(self, created_by_col: Column[UUID]) -> ColumnElement[bool]:
        """Строит WHERE-условие для фильтрации записей по правам доступа.

        Parameters
        ----------
        created_by_col : Column[UUID]
            Колонка таблицы, содержащая идентификатор создателя записи.

        Returns
        -------
        ColumnElement[bool]
            SQLAlchemy-выражение, готовое к использованию в `.where()`.
        """
        if self.partner_id is not None:
            return created_by_col.in_([self.user_id, self.partner_id])

        return created_by_col == self.user_id

    model_config = ConfigDict(frozen=True)


class RepositoryInterfaceNew(ABC):
    """Базовый класс всех репозиториев.

    Реализует паттерн Repository (DAO). Хранит подключение к базе данных
    и предоставляет вспомогательные методы для построения запросов,
    общие для всех репозиториев.

    Attributes
    ----------
    connection : AsyncConnection
        Объект асинхронного подключения запроса.
    """

    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    @staticmethod
    def _build_count_query(
        table: Table, *where_clauses: ColumnElement[bool]
    ) -> Select[tuple[int]]:
        """Создаёт запрос подсчёта записей.

        Parameters
        ----------
        table : Table
            Таблица, по которой выполняется подсчёт.
        where_clauses : ColumnElement[bool]
            Условия WHERE для фильтрации. Если не переданы,
            возвращается запрос без фильтрации.

        Returns
        -------
        Select[tuple[int]]
            Запрос для подсчёта общего количества записей.
        """
        query = select(func.count().label("count_1")).select_from(table)

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
            Выражение сортировки в заданном направлении.
        """
        return column.desc() if order == SortOrder.DESC else column.asc()


class OwnedRepositoryInterface(RepositoryInterfaceNew):
    """Интерфейс репозитория для сущностей с ограниченным доступом.

    Предназначен для сущностей, видимых только владельцу и его партнёру.
    Объединяет полный набор CRUD-операций с атомарной проверкой
    принадлежности через AccessContext.
    """

    @staticmethod
    def _creator_columns() -> list[Label[Any]]:
        """Возвращает лейблированные колонки пользователя для JOIN-запросов.

        Используется для избежания конфликта имён при джойне с таблицами,
        содержащими аналогичные базовые колонки (id, created_at).

        Returns
        -------
        list[Label[Any]]
            Список лейблированных колонок users_table.
        """
        return [
            users_table.c.id.label("creator_id"),
            users_table.c.created_at.label("creator_created_at"),
            users_table.c.username.label("creator_username"),
            users_table.c.avatar_url.label("creator_avatar_url"),
            users_table.c.is_active.label("creator_is_active"),
        ]

    @staticmethod
    def _extract_creator(row: RowMapping) -> dict[str, Any]:
        """Извлекает данные создателя из плоской строки JOIN-результата.

        Parameters
        ----------
        row : RowMapping
            Плоская строка результата запроса с лейблированными
            колонками пользователя.

        Returns
        -------
        dict[str, Any]
            Словарь с данными создателя, готовый для вложенной валидации DTO.
        """
        return {
            "id": row["creator_id"],
            "created_at": row["creator_created_at"],
            "username": row["creator_username"],
            "avatar_url": row["creator_avatar_url"],
            "is_active": row["creator_is_active"],
        }


class CreateMixin(ABC, Generic[CreateDTO, EntityDTO]):
    """Миксин операции создания записи.

    Attributes
    ----------
    CreateDTO : TypeVar
        Тип DTO для создания записи.
    EntityDTO : TypeVar
        Тип доменного DTO возвращаемой сущности.
    """

    @abstractmethod
    async def create(self, create_dto: CreateDTO) -> EntityDTO:
        """Создаёт новую запись.

        Parameters
        ----------
        create_dto : CreateDTO
            Данные для создания записи.

        Returns
        -------
        EntityDTO
            Доменное DTO созданной записи.
        """
        ...


class OwnedCreateMixin(OwnedRepositoryInterface, Generic[CreateDTO, EntityDTO]):
    """Миксин операции создания записи с явной привязкой к владельцу.

    Предназначен для сущностей с ограниченной видимостью, у которых
    поле created_by не входит в схему запроса и извлекается отдельно
    из payload токена на уровне сервиса.

    Attributes
    ----------
    CreateDTO : TypeVar
        Тип DTO для создания записи.
    EntityDTO : TypeVar
        Тип доменного DTO возвращаемой сущности.
    """

    @abstractmethod
    async def create(self, create_dto: CreateDTO, created_by: UUID) -> EntityDTO:
        """Создаёт новую запись с привязкой к владельцу.

        Parameters
        ----------
        create_dto : CreateDTO
            Данные для создания записи.
        created_by : UUID
            Идентификатор пользователя, создающего запись.
            Передаётся явно, так как извлекается из payload токена,
            а не из схемы запроса.

        Returns
        -------
        EntityDTO
            Доменное DTO созданной записи.
        """
        ...


class ReadMixin(ABC, Generic[EntityDTO]):
    """Миксин операции чтения записи по идентификатору.

    Attributes
    ----------
    EntityDTO : TypeVar
        Тип доменного DTO возвращаемой сущности.
    """

    # @abstractmethod
    # async def get_all(
    #     self,
    #     *,
    #     offset: int = 0,
    #     limit: int = 50,
    #     sort_order: SortOrder = SortOrder.DESC,
    # ) -> tuple[list[EntityDTO], int]:
    #     """Возвращает постраничный список всех записей и их общее количество.

    #     Parameters
    #     ----------
    #     offset : int, optional
    #         Количество пропускаемых записей, по умолчанию 0.
    #     limit : int, optional
    #         Максимальное количество возвращаемых записей, по умолчанию 50.
    #     sort_order : SortOrder, optional
    #         Направление сортировки по полю `created_at`,
    #         по умолчанию SortOrder.DESC.

    #     Returns
    #     -------
    #     tuple[list[EntityDTO], int]
    #         Список DTO и общее количество записей без учёта пагинации.
    #     """
    #     ...

    @abstractmethod
    async def get_by_id(self, record_id: UUID) -> EntityDTO | None:
        """Возвращает запись по идентификатору.

        Parameters
        ----------
        record_id : UUID
            Идентификатор записи для получения.

        Returns
        -------
        EntityDTO | None
            Доменное DTO найденной записи или None, если запись не найдена.
        """
        ...


class OwnedReadMixin(OwnedRepositoryInterface, Generic[EntityDTO]):
    """Миксин операции чтения записи с проверкой прав доступа.

    Предназначен для сущностей с ограниченной видимостью. Условие доступа
    из AccessContext включается непосредственно в WHERE-clause запроса,
    исключая TOCTOU.

    Attributes
    ----------
    EntityDTO : TypeVar
        Тип доменного DTO возвращаемой сущности.
    """

    @abstractmethod
    async def get_all(
        self,
        access_ctx: AccessContext,
        *,
        offset: int = DEFAULT_OFFSET,
        limit: int = DEFAULT_LIMIT,
        sort_order: SortOrder = SortOrder.DESC,
    ) -> tuple[list[EntityDTO], int]:
        """Возвращает постраничный список записей, доступных в рамках контекста.

        Условие доступа применяется на уровне запроса - результат содержит
        только записи, видимые для указанного владельца и партнёра.

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
            по умолчанию SortOrder.DESC.

        Returns
        -------
        tuple[list[EntityDTO], int]
            Список DTO и общее количество записей без учёта пагинации.
        """
        ...

    @abstractmethod
    async def get_by_id(
        self, record_id: UUID, access_ctx: AccessContext
    ) -> EntityDTO | None:
        """Возвращает запись по идентификатору при наличии прав доступа.

        Намеренно не разграничивает отсутствие записи и отказ в доступе -
        это предотвращает раскрытие факта существования чужих записей.

        Parameters
        ----------
        record_id : UUID
            Идентификатор запрашиваемой записи.
        access_ctx : AccessContext
            Контекст доступа с идентификаторами владельца и партнёра.

        Returns
        -------
        EntityDTO | None
            Доменное DTO найденной записи или None, если запись
            не найдена либо доступ запрещён.
        """
        ...


class OwnedFilteredReadMixin(OwnedRepositoryInterface, Generic[FilterDTO, EntityDTO]):
    """Миксин операции фильтрованного чтения с подсчётом записей.

    Предназначен для сущностей с ограниченным доступом, поддерживающих
    доменно-специфичную фильтрацию. Возвращает результат совместно
    с общим количеством записей для пагинации на клиенте.

    Attributes
    ----------
    FilterDTO : TypeVar
        Тип DTO с параметрами фильтрации. Специфичен для домена -
        определяется в конкретном интерфейсе репозитория.
    EntityDTO : TypeVar
        Тип доменного DTO возвращаемой сущности.
    """

    @abstractmethod
    async def get_all(
        self,
        filter_dto: FilterDTO,
        access_ctx: AccessContext,
        *,
        offset: int = DEFAULT_OFFSET,
        limit: int = DEFAULT_LIMIT,
        sort_order: SortOrder = SortOrder.DESC,
    ) -> tuple[list[EntityDTO], int]:
        """Возвращает отфильтрованный список записей и общее их количество.

        Parameters
        ----------
        filter_dto : FilterDTO
            Доменно-специфичные параметры фильтрации.
        access_ctx : AccessContext
            Контекст доступа с идентификаторами владельца и партнёра.
        offset : int, optional
            Количество пропускаемых записей, по умолчанию `DEFAULT_OFFSET`.
        limit : int, optional
            Максимальное количество возвращаемых записей, по умолчанию `DEFAULT_LIMIT`.
        sort_order : SortOrder, optional
            Направление сортировки по полю `created_at`,
            по умолчанию SortOrder.DESC.

        Returns
        -------
        tuple[list[EntityDTO], int]
            Список DTO и общее количество записей без учёта пагинации.
        """
        ...


class UpdateMixin(ABC, Generic[UpdateDTO, EntityDTO]):
    """Миксин операции обновления записи без проверки прав доступа.

    Предназначен для публичных сущностей, не имеющих ограничений
    на изменение по принадлежности.

    Attributes
    ----------
    UpdateDTO : TypeVar
        Тип DTO для обновления записи.
    EntityDTO : TypeVar
        Тип доменного DTO возвращаемой сущности.
    """

    @abstractmethod
    async def update(self, record_id: UUID, update_dto: UpdateDTO) -> EntityDTO | None:
        """Обновляет запись по идентификатору.

        Parameters
        ----------
        record_id : UUID
            Идентификатор обновляемой записи.
        update_dto : UpdateDTO
            Новые данные для записи.

        Returns
        -------
        EntityDTO | None
            Доменное DTO обновлённой записи или None, если запись не найдена.
        """
        ...


class OwnedUpdateMixin(OwnedRepositoryInterface, Generic[UpdateDTO, EntityDTO]):
    """Миксин операции обновления записи с проверкой прав доступа.

    Предназначен для сущностей с ограниченной видимостью. Условие доступа
    из AccessContext включается непосредственно в WHERE-clause запроса,
    обеспечивая атомарность проверки и обновления (исключает TOCTOU).

    Attributes
    ----------
    UpdateDTO : TypeVar
        Тип DTO для обновления записи.
    EntityDTO : TypeVar
        Тип доменного DTO возвращаемой сущности.
    """

    @abstractmethod
    async def update(
        self,
        record_id: UUID,
        update_dto: UpdateDTO,
        access_ctx: AccessContext,
    ) -> EntityDTO | None:
        """Обновляет запись при наличии прав доступа.

        Намеренно не разграничивает отсутствие записи и отказ в доступе -
        это предотвращает раскрытие факта существования чужих записей.

        Parameters
        ----------
        record_id : UUID
            Идентификатор обновляемой записи.
        update_dto : UpdateDTO
            Новые данные для записи.
        access_ctx : AccessContext
            Контекст доступа с идентификаторами владельца и партнёра.

        Returns
        -------
        EntityDTO | None
            Доменное DTO обновлённой записи или None, если запись
            не найдена либо доступ запрещён.
        """
        ...


class DeleteMixin(ABC):
    """Миксин операции удаления записи без проверки прав доступа.

    Предназначен для публичных сущностей или административных операций,
    не требующих проверки принадлежности.
    """

    @abstractmethod
    async def delete(self, record_id: UUID) -> bool:
        """Удаляет запись по идентификатору.

        Parameters
        ----------
        record_id : UUID
            Идентификатор удаляемой записи.

        Returns
        -------
        bool
            True, если запись была удалена. False, если запись не найдена.
        """
        ...


class OwnedDeleteMixin(OwnedRepositoryInterface):
    """Миксин операции удаления записи с проверкой прав доступа.

    Предназначен для сущностей с ограниченной видимостью. Условие доступа
    из AccessContext включается непосредственно в WHERE-clause запроса,
    обеспечивая атомарность проверки и удаления (исключает TOCTOU).
    """

    @abstractmethod
    async def delete(self, record_id: UUID, access_ctx: AccessContext) -> bool:
        """Удаляет запись при наличии прав доступа.

        Намеренно не разграничивает отсутствие записи и отказ в доступе -
        это предотвращает раскрытие факта существования чужих записей.

        Parameters
        ----------
        record_id : UUID
            Идентификатор удаляемой записи.
        access_ctx : AccessContext
            Контекст доступа с идентификаторами владельца и партнёра.

        Returns
        -------
        bool
            True, если запись была удалена. False, если запись не найдена
            либо доступ запрещён.
        """
        ...
