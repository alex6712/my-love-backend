from abc import ABC, abstractmethod
from typing import Any, Generic, Sequence, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, FromClause, Label, RowMapping, Select, func, select
from sqlalchemy.ext.asyncio import AsyncConnection
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
        table: FromClause, *where_clauses: ColumnElement[bool]
    ) -> Select[tuple[int]]:
        """Создаёт запрос подсчёта записей.

        Parameters
        ----------
        table : FromClause
            Таблица или выражение, по которой выполняется подсчёт.
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


class OwnedRepositoryInterface(RepositoryInterface):
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
            users_table.c.id.label("_creator_id"),
            users_table.c.created_at.label("_creator_created_at"),
            users_table.c.username.label("_creator_username"),
            users_table.c.avatar_url.label("_creator_avatar_url"),
            users_table.c.is_active.label("_creator_is_active"),
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
            "id": row["_creator_id"],
            "created_at": row["_creator_created_at"],
            "username": row["_creator_username"],
            "avatar_url": row["_creator_avatar_url"],
            "is_active": row["_creator_is_active"],
        }


class CreateMixin(ABC, Generic[CreateDTO, EntityDTO]):
    """Миксин операции создания записи.

    Type Parameters
    ---------------
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

    Type Parameters
    ---------------
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


class OwnedBatchCreateMixin(ABC, Generic[CreateDTO, EntityDTO]):
    """Миксин операции пакетного создания записей с явной привязкой к владельцу.

    Предназначен для сущностей с ограниченной видимостью, у которых
    поле created_by не входит в схему запроса и извлекается отдельно
    из payload токена на уровне сервиса.

    Type Parameters
    ---------------
    CreateDTO : TypeVar
        Тип DTO для создания записи.
    EntityDTO : TypeVar
        Тип доменного DTO возвращаемой сущности.
    """

    @abstractmethod
    async def create_batch(
        self, create_dtos: Sequence[CreateDTO], created_by: UUID
    ) -> list[EntityDTO]:
        """Создаёт несколько записей с привязкой к владельцу.

        Parameters
        ----------
        create_dtos : Sequence[CreateDTO]
            Данные для создания записей.
        created_by : UUID
            Идентификатор пользователя, создающего записи.
            Передаётся явно, так как извлекается из payload токена,
            а не из схемы запроса.

        Returns
        -------
        list[EntityDTO]
            Список доменных DTO созданных записей.
            Порядок соответствует порядку create_dtos.
        """
        ...


class ReadOneMixin(ABC, Generic[EntityDTO]):
    """Миксин для операции получения одной записи по идентификатору.

    Type Parameters
    ---------------
    EntityDTO : TypeVar
        Тип доменного DTO возвращаемой сущности.
    """

    @abstractmethod
    async def get_one(self, record_id: UUID) -> EntityDTO | None:
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


class FilteredReadOneMixin(ABC, Generic[FilterDTO, EntityDTO]):
    """Миксин для получения одной сущности по фильтрам.

    Type Parameters
    ---------------
    FilterDTO
        DTO с полями фильтрации.
    EntityDTO
        DTO возвращаемой сущности.
    """

    @abstractmethod
    async def get_one_filtered(self, filter_dto: FilterDTO) -> EntityDTO | None:
        """Возвращает одну сущность, соответствующую переданным фильтрам.

        Parameters
        ----------
        filter_dto : FilterDTO
            DTO с полями фильтрации.

        Returns
        -------
        EntityDTO
            Найденная сущность.
        None
            Если ни одна запись не соответствует фильтрам.
        """
        ...


class ReadMixin(ReadOneMixin[EntityDTO]):
    """Миксин для полного набора read-операций: по идентификатору и списком.

    Расширяет :class:`ReadOneMixin`, добавляя постраничную выборку всех записей.

    Type Parameters
    ---------------
    EntityDTO : TypeVar
        Тип доменного DTO возвращаемой сущности.
    """

    @abstractmethod
    async def get_all(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        sort_order: SortOrder = SortOrder.DESC,
    ) -> tuple[list[EntityDTO], int]:
        """Возвращает постраничный список всех записей и их общее количество.

        Parameters
        ----------
        offset : int, optional
            Количество пропускаемых записей, по умолчанию 0.
        limit : int, optional
            Максимальное количество возвращаемых записей, по умолчанию 50.
        sort_order : SortOrder, optional
            Направление сортировки по полю `created_at`,
            по умолчанию SortOrder.DESC.

        Returns
        -------
        tuple[list[EntityDTO], int]
            Список DTO и общее количество записей без учёта пагинации.
        """
        ...


class FilteredReadMixin(ABC, Generic[FilterDTO, EntityDTO]):
    """Миксин операции фильтрованного чтения с подсчётом записей.

    Предназначен для публичных сущностей, не имеющих ограничений доступа
    по принадлежности, но поддерживающих доменно-специфичную фильтрацию.
    Возвращает результат совместно с общим количеством записей
    для пагинации на клиенте.

    В отличие от :class:`OwnedFilteredReadMixin`, не требует
    :class:`AccessContext` — фильтрация определяется исключительно
    параметрами -filter_dto-.

    Type Parameters
    ---------------
    FilterDTO : TypeVar
        Тип DTO с параметрами фильтрации. Специфичен для домена —
        определяется в конкретном интерфейсе репозитория.
    EntityDTO : TypeVar
        Тип доменного DTO возвращаемой сущности.
    """

    @abstractmethod
    async def get_filtered(
        self,
        filter_dto: FilterDTO,
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
        offset : int, optional
            Количество пропускаемых записей, по умолчанию `DEFAULT_OFFSET`.
        limit : int, optional
            Максимальное количество возвращаемых записей, по умолчанию `DEFAULT_LIMIT`.
        sort_order : SortOrder, optional
            Направление сортировки по полю `created_at`,
            по умолчанию `SortOrder.DESC`.

        Returns
        -------
        tuple[list[EntityDTO], int]
            Список DTO и общее количество записей без учёта пагинации.
        """
        ...


class OwnedReadMixin(ABC, Generic[EntityDTO]):
    """Миксин операции чтения записи с проверкой прав доступа.

    Предназначен для сущностей с ограниченной видимостью. Условие доступа
    из AccessContext включается непосредственно в WHERE-clause запроса,
    исключая TOCTOU.

    Type Parameters
    ---------------
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
    async def get_one(
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


class OwnedFilteredReadMixin(ABC, Generic[FilterDTO, EntityDTO]):
    """Миксин операции фильтрованного чтения с подсчётом записей.

    Предназначен для сущностей с ограниченным доступом, поддерживающих
    доменно-специфичную фильтрацию. Возвращает результат совместно
    с общим количеством записей для пагинации на клиенте.

    Type Parameters
    ---------------
    FilterDTO : TypeVar
        Тип DTO с параметрами фильтрации. Специфичен для домена -
        определяется в конкретном интерфейсе репозитория.
    EntityDTO : TypeVar
        Тип доменного DTO возвращаемой сущности.
    """

    @abstractmethod
    async def get_filtered(
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


class OwnedBatchReadMixin(ABC, Generic[EntityDTO]):
    """Миксин операции пакетного чтения записей с проверкой прав доступа.

    Предназначен для сущностей с ограниченной видимостью. Условие доступа
    из AccessContext включается непосредственно в WHERE-clause запроса,
    исключая TOCTOU.

    Type Parameters
    ---------------
    EntityDTO : TypeVar
        Тип доменного DTO возвращаемой сущности.
    """

    @abstractmethod
    async def get_by_ids(
        self, record_ids: Sequence[UUID], access_ctx: AccessContext
    ) -> list[EntityDTO]:
        """Возвращает записи по списку идентификаторов при наличии прав доступа.

        Намеренно не разграничивает отсутствие записи и отказ в доступе -
        недоступные и несуществующие записи молча исключаются из результата.
        Это предотвращает раскрытие факта существования чужих записей.

        Parameters
        ----------
        record_ids : Sequence[UUID]
            Идентификаторы запрашиваемых записей.
        access_ctx : AccessContext
            Контекст доступа с идентификаторами владельца и партнёра.

        Returns
        -------
        list[EntityDTO]
            Список DTO записей, доступных в рамках контекста.
            Порядок не гарантирован. Размер списка может быть меньше
            len(record_ids), если часть записей недоступна или не существует.
        """
        ...


class UpdateMixin(ABC, Generic[UpdateDTO, EntityDTO]):
    """Миксин операции обновления записи без проверки прав доступа.

    Предназначен для публичных сущностей, не имеющих ограничений
    на изменение по принадлежности.

    Type Parameters
    ---------------
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


class FilteredUpdateMixin(ABC, Generic[FilterDTO, UpdateDTO, EntityDTO]):
    """Миксин операции обновления записи с фильтрацией по дополнительным критериям.

    Предназначен для сущностей, обновление которых требует проверки
    дополнительных условий помимо идентификатора записи - например,
    принадлежности конкретному внешнему другому агрегату.

    В отличие от :class:`UpdateMixin`, принимает `filter_dto` вместо
    `record_id`, что позволяет инкапсулировать произвольный набор
    критериев фильтрации без расширения сигнатуры базового контракта.

    Type Parameters
    ---------------
    FilterDTO : TypeVar
        Доменно-специфичные параметры фильтрации.
    UpdateDTO : TypeVar
        Тип DTO с новыми данными для записи.
    EntityDTO : TypeVar
        Тип доменного DTO возвращаемой сущности.
    """

    @abstractmethod
    async def update_filtered(
        self, filter_dto: FilterDTO, update_dto: UpdateDTO
    ) -> EntityDTO | None:
        """Обновляет запись по набору критериев фильтрации.

        Parameters
        ----------
        filter_dto : FilterDTO
            Критерии выборки обновляемой записи. Конкретный состав полей
            определяется реализацией репозитория.
        update_dto : UpdateDTO
            Новые данные для записи.

        Returns
        -------
        EntityDTO | None
            Доменное DTO обновлённой записи или None, если запись,
            удовлетворяющая критериям фильтрации, не найдена.
        """
        ...


class OwnedUpdateMixin(ABC, Generic[UpdateDTO, EntityDTO]):
    """Миксин операции обновления записи с проверкой прав доступа.

    Предназначен для сущностей с ограниченной видимостью. Условие доступа
    из AccessContext включается непосредственно в WHERE-clause запроса,
    обеспечивая атомарность проверки и обновления (исключает TOCTOU).

    Type Parameters
    ---------------
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


class DeleteMixin(ABC, Generic[EntityDTO]):
    """Миксин операции удаления записи без проверки прав доступа.

    Предназначен для публичных сущностей или административных операций,
    не требующих проверки принадлежности.

    Type Parameters
    ---------------
    EntityDTO : TypeVar
        Тип доменного DTO возвращаемой сущности.
    """

    @abstractmethod
    async def delete(self, record_id: UUID) -> EntityDTO | None:
        """Удаляет запись по идентификатору.

        Parameters
        ----------
        record_id : UUID
            Идентификатор удаляемой записи.

        Returns
        -------
        EntityDTO | None
            Доменное DTO удалённой записи или None, если запись
            не найдена либо доступ запрещён.
        """
        ...


class OwnedDeleteMixin(ABC, Generic[EntityDTO]):
    """Миксин операции удаления записи с проверкой прав доступа.

    Предназначен для сущностей с ограниченной видимостью. Условие доступа
    из AccessContext включается непосредственно в WHERE-clause запроса,
    обеспечивая атомарность проверки и удаления (исключает TOCTOU).

    Type Parameters
    ---------------
    EntityDTO : TypeVar
        Тип доменного DTO возвращаемой сущности.
    """

    @abstractmethod
    async def delete(
        self, record_id: UUID, access_ctx: AccessContext
    ) -> EntityDTO | None:
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
        EntityDTO | None
            Доменное DTO удалённой записи или None, если запись
            не найдена либо доступ запрещён.
        """
        ...


class OwnedBatchDeleteMixin(ABC, Generic[EntityDTO]):
    """Миксин операции пакетного удаления записей с проверкой прав доступа.

    Предназначен для сущностей с ограниченной видимостью. Условие доступа
    из AccessContext включается непосредственно в WHERE-clause запроса,
    обеспечивая атомарность проверки и удаления (исключает TOCTOU).

    Type Parameters
    ---------------
    EntityDTO : TypeVar
        Тип доменного DTO возвращаемой сущности.
    """

    @abstractmethod
    async def delete_batch(
        self, record_ids: Sequence[UUID], access_ctx: AccessContext
    ) -> list[EntityDTO]:
        """Удаляет записи по списку идентификаторов при наличии прав доступа.

        Намеренно не разграничивает отсутствие записи и отказ в доступе -
        недоступные и несуществующие записи молча пропускаются.
        Это предотвращает раскрытие факта существования чужих записей.

        Parameters
        ----------
        record_ids : Sequence[UUID]
            Идентификаторы удаляемых записей.
        access_ctx : AccessContext
            Контекст доступа с идентификаторами владельца и партнёра.

        Returns
        -------
        list[EntityDTO]
            Список DTO удалённых записей.
            Пустой список, если записей нет или доступ ко всем из них запрещён.
        """
        ...
