from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, Label, RowMapping, Select, Table, func, select
from sqlalchemy.ext.asyncio import AsyncConnection
from sqlalchemy.sql.elements import ColumnElement, UnaryExpression

from app.core.enums import SortOrder
from app.infra.postgres.tables import users_table
from app.schemas.dto.base import BaseCreateDTO, BaseSQLCoreDTO, BaseUpdateDTO

CreateDTO = TypeVar("CreateDTO", bound=BaseCreateDTO)
UpdateDTO = TypeVar("UpdateDTO", bound=BaseUpdateDTO)
EntityDTO = TypeVar("EntityDTO", bound=BaseSQLCoreDTO)


class AccessContext(BaseModel):
    """Контекст доступа к записи с ограниченной видимостью.

    Используется для атомарной проверки прав владения при мутациях
    и фильтрации выборок. Условие доступа включается непосредственно
    в WHERE-clause запроса, исключая TOCTOU.

    Attributes
    ----------
    creator_id : UUID
        Идентификатор пользователя, выполняющего запрос.
    partner_id : UUID | None
        Идентификатор партнёра пользователя. Если передан,
        доступ распространяется и на его записи.
    """

    model_config = ConfigDict(frozen=True)

    creator_id: UUID
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
            return created_by_col.in_([self.creator_id, self.partner_id])
        return created_by_col == self.creator_id


class RepositoryInterface(ABC):
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
            Выражение сортировки в заданном направлении.
        """
        return column.desc() if order == SortOrder.DESC else column.asc()


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


class OwnedCreateMixin(ABC, Generic[CreateDTO, EntityDTO]):
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


class OwnedReadMixin(ABC, Generic[EntityDTO]):
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
    async def get_by_id(
        self, record_id: UUID, access_ctx: AccessContext
    ) -> EntityDTO | None:
        """Возвращает запись по идентификатору при наличии прав доступа.

        Намеренно не разграничивает отсутствие записи и отказ в доступе —
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


class OwnedUpdateMixin(ABC, Generic[UpdateDTO, EntityDTO]):
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

        Намеренно не разграничивает отсутствие записи и отказ в доступе —
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


class OwnedDeleteMixin(ABC):
    """Миксин операции удаления записи с проверкой прав доступа.

    Предназначен для сущностей с ограниченной видимостью. Условие доступа
    из AccessContext включается непосредственно в WHERE-clause запроса,
    обеспечивая атомарность проверки и удаления (исключает TOCTOU).
    """

    @abstractmethod
    async def delete(self, record_id: UUID, access_ctx: AccessContext) -> bool:
        """Удаляет запись при наличии прав доступа.

        Намеренно не разграничивает отсутствие записи и отказ в доступе —
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


class PublicRepositoryInterface(
    RepositoryInterface,
    CreateMixin[CreateDTO, EntityDTO],
    ReadMixin[EntityDTO],
    UpdateMixin[UpdateDTO, EntityDTO],
    DeleteMixin,
    Generic[CreateDTO, UpdateDTO, EntityDTO],
):
    """Интерфейс репозитория для публичных сущностей.

    Предназначен для сущностей без ограничений доступа по владельцу.
    Объединяет полный набор CRUD-операций без проверки принадлежности.
    """

    pass


class OwnedRepositoryInterface(
    RepositoryInterface,
    OwnedCreateMixin[CreateDTO, EntityDTO],
    OwnedReadMixin[EntityDTO],
    OwnedUpdateMixin[UpdateDTO, EntityDTO],
    OwnedDeleteMixin,
    Generic[CreateDTO, UpdateDTO, EntityDTO],
):
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
