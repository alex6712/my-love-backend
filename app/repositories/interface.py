from abc import ABC, abstractmethod
from collections.abc import Collection
from typing import Any, Generic, Iterable, Sequence, TypeVar, cast
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import (
    Column,
    FromClause,
    Label,
    RowMapping,
    Select,
    Table,
    func,
    select,
    true,
)
from sqlalchemy.ext.asyncio import AsyncConnection
from sqlalchemy.sql.elements import ColumnElement, UnaryExpression

from app.core.consts import DEFAULT_LIMIT, DEFAULT_OFFSET
from app.core.enums import SortOrder
from app.core.filtering import (
    EQ,
    IN,
    ColumnAlias,
    EqOp,
    FilterOp,
    GteOp,
    InOp,
    IsNullOp,
    LikeOp,
    LteOp,
)
from app.core.types import is_set
from app.schemas.dto.base import (
    BaseCreateDTO,
    BaseFilterDTO,
    BaseFilterManyDTO,
    BaseFilterOneDTO,
    BaseSQLCoreDTO,
    BaseUpdateDTO,
)

EntityDTO = TypeVar("EntityDTO", bound=BaseSQLCoreDTO)
FilterOneDTO = TypeVar("FilterOneDTO", bound=BaseFilterOneDTO)
FilterManyDTO = TypeVar("FilterManyDTO", bound=BaseFilterManyDTO)
CreateDTO = TypeVar("CreateDTO", bound=BaseCreateDTO)
UpdateDTO = TypeVar("UpdateDTO", bound=BaseUpdateDTO)


class AccessContext(ABC, BaseModel):
    """Абстрактный контекст доступа для формирования SQL-ограничений.

    Контекст доступа инкапсулирует правила видимости записей и
    используется для построения WHERE-условий на уровне запроса.

    Реализации должны возвращать корректное SQLAlchemy-выражение,
    которое ограничивает доступ к данным в соответствии с
    текущим контекстом пользователя.
    """

    @abstractmethod
    def as_where_clause(self, created_by_col: Column[UUID]) -> ColumnElement[bool]:
        """Сформировать WHERE-условие для ограничения доступа.

        Parameters
        ----------
        created_by_col : Column[UUID]
            Колонка, содержащая идентификатор владельца записи.

        Returns
        -------
        ColumnElement[bool]
            SQLAlchemy-выражение, которое может быть передано в `.where()`.

        Notes
        -----
        - Метод не должен выполнять запросы - только строить выражение.
        - Возвращаемое выражение должно быть детерминированным.
        - Не должно происходить побочных эффектов.
        """
        ...


class PublicAccessContext(AccessContext):
    """Контекст доступа без ограничений видимости.

    Используется для публичных ресурсов, где проверка
    прав владения не требуется. WHERE-условие всегда
    допускает все записи.
    """

    def as_where_clause(self, created_by_col: Column[UUID]) -> ColumnElement[bool]:
        """Сформировать WHERE-условие без ограничений доступа.

        Parameters
        ----------
        created_by_col : Column[UUID]
            Колонка, содержащая идентификатор владельца записи.
            Не используется.

        Returns
        -------
        ColumnElement[bool]
            SQLAlchemy-выражение, эквивалентное `true()`,
            не накладывающее ограничений на выборку.
        """
        return true()


class CoupleAccessContext(AccessContext):
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

    @staticmethod
    def _label_columns(
        columns: Iterable[ColumnElement[Any]], prefix: str
    ) -> list[Label[Any]]:
        """Применяет префиксные лейблы к колонкам для SELECT.

        Используется при JOIN нескольких алиасов одной таблицы
        во избежание коллизий имён колонок в результирующей строке.
        Лейбл формируется как `_{prefix}_{column.key}`.

        Parameters
        ----------
        columns : Iterable[ColumnElement[Any]]
            Колонки для лейблирования.
        prefix : str
            Префикс, добавляемый к имени каждой колонки.

        Returns
        -------
        list[Label[Any]]
            Список лейблированных колонок.
        """
        return [col.label(f"_{prefix}_{col.key}") for col in columns]

    @staticmethod
    def _extract_prefixed(
        row: RowMapping, prefix: str, fields: Iterable[str]
    ) -> dict[str, Any]:
        """Извлекает префиксированные поля из плоской строки запроса.

        Парный метод к `_label_columns` - читает из `RowMapping`
        поля, ранее лейблированные через `_{prefix}_{field}`,
        и возвращает словарь без префикса для последующей валидации в DTO.

        Parameters
        ----------
        row : RowMapping
            Плоская строка результата запроса.
        prefix : str
            Префикс, под которым были лейблированы колонки.
        fields : Iterable[str]
            Имена полей без префикса.

        Returns
        -------
        dict[str, Any]
            Словарь вида `{field: value}`.
        """
        return {field: row[f"_{prefix}_{field}"] for field in fields}

    @staticmethod
    def _get_where_clauses() -> list[ColumnElement[bool]]:
        """Возвращает базовые WHERE-условия для запросов репозитория.

        Предназначен для переопределения в подклассах, где требуется
        добавить фиксированные условия фильтрации (например, `is_deleted = False`).

        Returns
        -------
        list[ColumnElement[bool]]
            Пустой список - базовая реализация не накладывает ограничений.
        """
        return []

    @staticmethod
    def _build_filter_clauses(
        filter_dto: BaseFilterDTO, table: Table
    ) -> list[ColumnElement[bool]]:
        """Преобразует filter DTO в список WHERE-условий SQLAlchemy.

        Читает метаданные полей DTO из `Annotated`-аннотаций и строит
        соответствующие выражения SQLAlchemy Core. Поля со значением `UNSET`
        пропускаются. Оператор определяется маркером `FilterOp` в метаданных;
        если маркер отсутствует - выбирается дефолтный по типу значения:
        `IN` для списков, `EQ` для скаляров.

        Parameters
        ----------
        filter_dto : BaseFilterDTO
            DTO с критериями фильтрации. Поддерживает `BaseFilterOneDTO`
            и `BaseFilterManyDTO`.
        table : Table
            Таблица SQLAlchemy Core, по которой строятся условия.
            Колонки разрешаются через `table.c`.

        Returns
        -------
        list[ColumnElement[bool]]
            Список WHERE-условий для передачи в `.where(*clauses)`.
            Пустой список означает отсутствие фильтров.

        Raises
        ------
        AttributeError
            Если имя поля DTO (или псевдоним из `ColumnAlias`) не соответствует
            ни одной колонке в переданной таблице.
        NotImplementedError
            Если в метаданных поля обнаружен неизвестный подкласс `FilterOp`.

        Notes
        -----
        Маркеры читаются из `field_info.metadata` в порядке объявления.
        Берётся первый найденный экземпляр `FilterOp` и первый `ColumnAlias`.

        Examples
        --------
        >>> clauses = self._build_filter_clauses(filter_dto, users_table)
        >>> query = select(users_table).where(*clauses)
        """
        clauses: list[ColumnElement[bool]] = []

        for field_name, field_info in type(filter_dto).model_fields.items():
            if not is_set(value := getattr(filter_dto, field_name)):
                continue

            metadata = field_info.metadata

            alias = next(
                (m.name for m in metadata if isinstance(m, ColumnAlias)), field_name
            )
            op = next((m for m in metadata if isinstance(m, FilterOp)), None)

            column = table.c[alias]
            clause = RepositoryInterface.__resolve_clause(column, op, value)
            clauses.append(clause)

        return clauses

    @staticmethod
    def __resolve_clause(
        column: ColumnElement[Any],
        op: FilterOp | None,
        value: Any,
    ) -> ColumnElement[bool]:
        """Строит одно WHERE-условие по колонке, оператору и значению.

        Parameters
        ----------
        column : ColumnElement[Any]
            Колонка SQLAlchemy, по которой строится условие.
        op : FilterOp | None
            Маркер оператора из метаданных поля.
            Если `None` - оператор выбирается по типу `value`.
        value : Any
            Значение фильтра. Не может быть `Unset`.

        Returns
        -------
        ColumnElement[bool]
            Готовое выражение для WHERE.

        Raises
        ------
        NotImplementedError
            Если передан неизвестный подкласс `FilterOp`.
        """
        if op is None:
            op = IN if isinstance(value, Collection) else EQ

        match op:
            case EqOp():
                return column == value
            case InOp():
                return column.in_(
                    cast(
                        Collection[Any],
                        value if isinstance(value, Collection) else [value],
                    )
                )
            case LikeOp():
                return column.ilike(f"%{value}%")
            case GteOp():
                return column >= value
            case LteOp():
                return column <= value
            case IsNullOp():
                return column.is_(None) if value else column.is_not(None)
            case _:
                raise NotImplementedError(
                    f"Unknown filter operator: {type(op).__name__}"
                )


class Creator(RepositoryInterface, Generic[CreateDTO]):
    """Интерфейс для создания сущностей.

    Type Parameters
    ---------------
    CreateDTO : TypeVar
        Тип DTO для создания записи.
    """

    @abstractmethod
    async def create_one(self, create_dto: CreateDTO) -> bool:
        """Создать одну сущность.

        Parameters
        ----------
        create_dto : CreateDTO
            DTO с данными для создания.

        Returns
        -------
        bool
            True, если сущность была успешно создана, иначе False.
        """
        ...

    @abstractmethod
    async def create_many(self, create_dtos: Sequence[CreateDTO]) -> int:
        """Создать несколько сущностей.

        Parameters
        ----------
        create_dtos : Sequence[CreateDTO]
            Последовательность DTO для создания.

        Returns
        -------
        int
            Количество успешно созданных сущностей.
        """
        ...


class Reader(RepositoryInterface, Generic[FilterOneDTO, FilterManyDTO, EntityDTO]):
    """Интерфейс для чтения сущностей.

    Type Parameters
    ---------------
    FilterOneDTO : TypeVar
        Тип DTO для фильтрации записей (с гарантией одной сущности).
    FilterManyDTO : TypeVar
        Тип DTO для фильтрации записей.
    EntityDTO : TypeVar
        Тип доменного DTO возвращаемой сущности.
    """

    @abstractmethod
    async def read_one(
        self, filter_dto: FilterOneDTO, access_ctx: AccessContext
    ) -> EntityDTO | None:
        """Получить одну сущность.

        Parameters
        ----------
        filter_dto : FilterOneDTO
            DTO с критериями фильтрации.
        access_ctx : AccessContext
            Контекст доступа для ограничения видимости.

        Returns
        -------
        EntityDTO | None
            Найденная сущность или None, если запись отсутствует
            или недоступна.
        """
        ...

    @abstractmethod
    async def read_one_for_update(
        self, filter_dto: FilterOneDTO, access_ctx: AccessContext
    ) -> EntityDTO | None:
        """Получить одну сущность с блокировкой.

        Parameters
        ----------
        filter_dto : FilterOneDTO
            DTO с критериями фильтрации.
        access_ctx : AccessContext
            Контекст доступа для ограничения видимости.

        Returns
        -------
        EntityDTO | None
            Найденная сущность или None.

        Notes
        -----
        - Реализация должна использовать блокировку строки (например, SELECT ... FOR UPDATE).
        - Используется для безопасных мутаций без TOCTOU.
        """
        ...

    @abstractmethod
    async def read_many(
        self,
        filter_dto: FilterManyDTO,
        access_ctx: AccessContext,
        *,
        offset: int = DEFAULT_OFFSET,
        limit: int = DEFAULT_LIMIT,
        sort_order: SortOrder = SortOrder.DESC,
    ) -> tuple[list[EntityDTO], int]:
        """Получить список сущностей.

        Parameters
        ----------
        filter_dto : FilterManyDTO
            DTO с критериями фильтрации.
        access_ctx : AccessContext
            Контекст доступа для ограничения видимости.
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


class Updater(RepositoryInterface, Generic[FilterOneDTO, FilterManyDTO, UpdateDTO]):
    """Интерфейс для обновления сущностей.

    Type Parameters
    ---------------
    FilterOneDTO : TypeVar
        Тип DTO для фильтрации записей (с гарантией одной сущности).
    FilterManyDTO : TypeVar
        Тип DTO для фильтрации записей.
    UpdateDTO : TypeVar
        Тип DTO для обновления записей.
    """

    @abstractmethod
    async def update_one(
        self, filter_dto: FilterOneDTO, update_dto: UpdateDTO, access_ctx: AccessContext
    ) -> bool:
        """Обновить одну сущность.

        Parameters
        ----------
        filter_dto : FilterOneDTO
            DTO с критериями выбора сущности.
        update_dto : UpdateDTO
            DTO с изменяемыми полями.
        access_ctx : AccessContext
            Контекст доступа.

        Returns
        -------
        bool
            True, если сущность была обновлена, иначе False.
        """
        ...

    @abstractmethod
    async def update_many(
        self,
        filter_dto: FilterManyDTO,
        update_dto: UpdateDTO,
        access_ctx: AccessContext,
    ) -> int:
        """Обновить несколько сущностей.

        Parameters
        ----------
        filter_dto : FilterManyDTO
            DTO с критериями фильтрации.
        update_dto : UpdateDTO
            DTO с изменениями.
        access_ctx : AccessContext
            Контекст доступа.

        Returns
        -------
        int
            Количество обновлённых сущностей.
        """
        ...


class Deleter(RepositoryInterface, Generic[FilterOneDTO, FilterManyDTO]):
    """Интерфейс для удаления сущностей.

    Type Parameters
    ---------------
    FilterOneDTO : TypeVar
        Тип DTO для фильтрации записей (с гарантией одной сущности).
    FilterManyDTO : TypeVar
        Тип DTO для фильтрации записей.
    """

    @abstractmethod
    async def delete_one(
        self, filter_dto: FilterOneDTO, access_ctx: AccessContext
    ) -> bool:
        """Удалить одну сущность.

        Parameters
        ----------
        filter_dto : FilterOneDTO
            DTO с критериями выбора сущности.
        access_ctx : AccessContext
            Контекст доступа.

        Returns
        -------
        bool
            True, если сущность была удалена, иначе False.
        """
        ...

    @abstractmethod
    async def delete_many(
        self, filter_dto: FilterManyDTO, access_ctx: AccessContext
    ) -> int:
        """Удалить несколько сущностей.

        Parameters
        ----------
        filter_dto : FilterManyDTO
            DTO с критериями фильтрации.
        access_ctx : AccessContext
            Контекст доступа.

        Returns
        -------
        int
            Количество удалённых сущностей.
        """
        ...
