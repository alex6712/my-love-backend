from typing import Any, Sequence

from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError

from app.core.consts import DEFAULT_LIMIT, DEFAULT_OFFSET
from app.core.enums import SortOrder
from app.core.exceptions.user import UsernameAlreadyExistsException
from app.infra.postgres.tables.users import users_table
from app.repositories.interface import (
    AccessContext,
    Creator,
    Reader,
    Updater,
)
from app.schemas.dto.user import (
    CreateUserDTO,
    FilterOneUserDTO,
    UpdateUserDTO,
    UserWithCredentialsDTO,
)


class UserRepository(
    Creator[CreateUserDTO],
    Reader[FilterOneUserDTO, Any, UserWithCredentialsDTO],
    Updater[FilterOneUserDTO, Any, UpdateUserDTO],
):
    """Репозиторий пользователя.

    Реализация паттерна Репозиторий. Является объектом доступа к данным (DAO).
    Реализует основные CRUD операции с пользователями.

    Attributes
    ----------
    connection : AsyncConnection
        Объект асинхронного подключения запроса.

    Methods
    -------
    create_one(create_dto)
        Добавляет в базу данных новую запись о пользователе.
    read_one(filter_dto, access_ctx)
        Возвращает DTO пользователя с учётными данными.
    read_one_for_update(filter_dto, access_ctx)
        Возвращает пользователя с блокировкой строки для последующего изменения.
    update_one(filter_dto, update_dto, access_ctx)
        Обновляет данные пользователя.
    """

    async def create_one(self, create_dto: CreateUserDTO) -> bool:
        """Добавляет в базу данных новую запись о пользователе.

        Parameters
        ----------
        create_dto : CreateUserDTO
            Необходимые для создания записи данные о пользователе.

        Returns
        -------
        bool
            True если пользователь успешно создан.

        Raises
        ------
        UsernameAlreadyExistsException
           Пользователь с переданным username уже существует.
        """
        try:
            result = await self.connection.execute(
                insert(users_table).values(**create_dto.to_create_values())
            )
        except IntegrityError as e:
            if "uq_users_username" in str(e):
                raise UsernameAlreadyExistsException(
                    detail=f"User with username={create_dto.username} already exists."
                ) from e

            raise

        return result.rowcount == 1

    async def create_many(self, create_dtos: Sequence[CreateUserDTO]) -> int:
        """Не поддерживается для данной сущности.

        Не предусмотрено создание множества пользователей за одну транзакцию,
        т.к. пользователь за один запрос может создать только одну учётную запись.
        """
        raise NotImplementedError(
            "Method 'create_many' is not implemented in UserRepository"
        )

    async def read_one(
        self, filter_dto: FilterOneUserDTO, access_ctx: AccessContext
    ) -> UserWithCredentialsDTO | None:
        """Возвращает DTO пользователя с учётными данными.

        Parameters
        ----------
        filter_dto : FilterOneUserDTO
            Параметры фильтрации.
        access_ctx : AccessContext
            Контекст доступа.

        Returns
        -------
        UserWithCredentialsDTO | None
            DTO записи пользователя, None - если пользователь по заданному фильтру
            не найден.
        """
        result = await self.connection.execute(
            select(users_table).where(
                *self._build_filter_clauses(filter_dto, users_table),
                access_ctx.as_where_clause(users_table),
            )
        )

        if not (row := result.mappings().first()):
            return None

        return UserWithCredentialsDTO.model_validate(row)

    async def read_one_for_update(
        self, filter_dto: FilterOneUserDTO, access_ctx: AccessContext
    ) -> UserWithCredentialsDTO | None:
        """Возвращает пользователя с блокировкой строки для последующего изменения.

        Устанавливает `SELECT ... FOR UPDATE` - строка блокируется
        до завершения транзакции. Должен вызываться внутри транзакции.

        Parameters
        ----------
        filter_dto : FilterOneNoteDTO
            DTO с полями фильтрации.
        access_ctx : AccessContext
            Контекст доступа.

        Returns
        -------
        UserWithCredentialsDTO | None
            Найденный пользователь или None, если ни один пользователь
            не соответствует фильтрам.
        """
        result = await self.connection.execute(
            select(users_table)
            .where(
                *self._build_filter_clauses(filter_dto, users_table),
                access_ctx.as_where_clause(users_table),
            )
            .with_for_update()
        )

        if not (row := result.mappings().first()):
            return None

        return UserWithCredentialsDTO.model_validate(row)

    async def read_many(
        self,
        filter_dto: Any,
        access_ctx: AccessContext,
        *,
        offset: int = DEFAULT_OFFSET,
        limit: int = DEFAULT_LIMIT,
        sort_order: SortOrder = SortOrder.DESC,
    ) -> tuple[list[UserWithCredentialsDTO], int]:
        """Не поддерживается для данной сущности.

        Не предусмотрено чтение данных множества пользователей,
        т.к. не существует возможности просматривать списка пользователей.
        """
        raise NotImplementedError(
            "Method 'read_many' is not implemented in UserRepository"
        )

    async def update_one(
        self,
        filter_dto: FilterOneUserDTO,
        update_dto: UpdateUserDTO,
        access_ctx: AccessContext,
    ) -> bool:
        """Обновляет данные пользователя.

        Parameters
        ----------
        filter_dto : FilterOneUserDTO
            Параметры фильтрации.
        update_dto : UpdateUserDTO
            Новые данные пользователя.
        access_ctx : AccessContext
            Контекст доступа.

        Returns
        -------
        bool
            True если пользователь найден и успешно обновлён.
        """
        result = await self.connection.execute(
            update(users_table)
            .values(**update_dto.to_update_values())
            .where(
                *self._build_filter_clauses(filter_dto, users_table),
                access_ctx.as_where_clause(users_table),
            )
        )

        return result.rowcount == 1
