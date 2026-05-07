from typing import Sequence

from sqlalchemy import delete, insert, select, update

from app.core.consts import DEFAULT_LIMIT, DEFAULT_OFFSET
from app.core.enums import SortOrder
from app.infra.postgres.tables.user_sessions import user_sessions_table
from app.repositories.interface import AccessContext, Creator, Deleter, Reader, Updater
from app.schemas.dto.user_session import (
    CreateUserSessionDTO,
    FilterManyUserSessionsDTO,
    FilterOneUserSessionDTO,
    UpdateUserSessionDTO,
    UserSessionDTO,
)


class UserSessionRepository(
    Creator[CreateUserSessionDTO],
    Reader[FilterOneUserSessionDTO, FilterManyUserSessionsDTO, UserSessionDTO],
    Updater[FilterOneUserSessionDTO, FilterManyUserSessionsDTO, UpdateUserSessionDTO],
    Deleter[FilterOneUserSessionDTO, FilterManyUserSessionsDTO],
):
    """Репозиторий для управления пользовательскими сессиями.

    Реализует CRUD-операции над таблицей пользовательских сессий
    через SQLAlchemy AsyncSession.

    Methods
    -------
    create_one(create_dto)
        Создаёт новую пользовательскую сессию.
    read_one(filter_dto, access_ctx)
        Возвращает DTO пользовательской сессии или None, если запись не найдена.
    update_one(filter_dto, update_dto, access_ctx)
        Обновляет данные пользовательской сессии.
    update_many(filter_dto, update_dto, access_ctx)
        Обновляет данные множества пользовательских сессий.
    delete_one(filter_dto, access_ctx)
        Удаляет запись о пользовательской сессии из базы данных.
    delete_many(filter_dto, access_ctx)
        Удаляет множество записей о пользовательских сессиях из базы данных.
    """

    async def create_one(self, create_dto: CreateUserSessionDTO) -> bool:
        """Создаёт новую пользовательскую сессию.

        Parameters
        ----------
        create_dto : CreateUserSessionDTO
            Необходимые для создания записи данные о сессии.

        Returns
        -------
        bool
            True если пользовательская сессия успешно создана.
        """
        result = await self.connection.execute(
            insert(user_sessions_table).values(**create_dto.to_create_values())
        )

        return result.rowcount == 1

    async def create_many(self, create_dtos: Sequence[CreateUserSessionDTO]) -> int:
        """Не поддерживается для данной сущности.

        Не предусмотрено создание множества сессий за одну транзакцию,
        т.к. на каждый пользовательский логин создаётся только одна сессия.
        """
        raise NotImplementedError(
            "Method 'create_many' is not implemented in UserSessionRepository"
        )

    async def read_one(
        self, filter_dto: FilterOneUserSessionDTO, access_ctx: AccessContext
    ) -> UserSessionDTO | None:
        """Возвращает DTO пользовательской сессии.

        Parameters
        ----------
        filter_dto : FilterOneUserSessionDTO
            Параметры фильтрации.
        access_ctx : AccessContext
            Контекст доступа.

        Returns
        -------
        UserSessionDTO | None
            Доменное DTO записи сессии, None - если сессия по заданному фильтру
            не найдена.
        """
        result = await self.connection.execute(
            select(user_sessions_table).where(
                *self._build_filter_clauses(filter_dto, user_sessions_table),
                access_ctx.as_where_clause(user_sessions_table),
            )
        )

        if not (row := result.mappings().first()):
            return None

        return UserSessionDTO.model_validate(row)

    async def read_one_for_update(
        self, filter_dto: FilterOneUserSessionDTO, access_ctx: AccessContext
    ) -> UserSessionDTO | None:
        """Не поддерживается для данной сущности.

        Не предусмотрено чтение данных сессии с блокировкой строки,
        т.к. не существует сценария получения дополнительных данных перед обновлением.
        """
        raise NotImplementedError(
            "Method 'read_one_for_update' is not implemented in UserSessionRepository"
        )

    async def read_many(
        self,
        filter_dto: FilterManyUserSessionsDTO,
        access_ctx: AccessContext,
        *,
        offset: int = DEFAULT_OFFSET,
        limit: int = DEFAULT_LIMIT,
        sort_order: SortOrder = SortOrder.DESC,
    ) -> list[UserSessionDTO]:
        """Не поддерживается для данной сущности.

        Не предусмотрено чтение данных множества сессий,
        т.к. пока не существует страницы просмотра открытых сессий.
        """
        raise NotImplementedError(
            "Method 'read_many' is not implemented in UserSessionRepository"
        )

    async def update_one(
        self,
        filter_dto: FilterOneUserSessionDTO,
        update_dto: UpdateUserSessionDTO,
        access_ctx: AccessContext,
    ) -> bool:
        """Обновляет данные пользовательской сессии.

        Parameters
        ----------
        filter_dto : FilterOneUserDTO
            Параметры фильтрации.
        update_dto : UpdateUserDTO
            Новые данные пользовательской сессии.
        access_ctx : AccessContext
            Контекст доступа.

        Returns
        -------
        bool
            True если сессия найдена и успешно обновлёна.
        """
        result = await self.connection.execute(
            update(user_sessions_table)
            .values(**update_dto.to_update_values())
            .where(
                *self._build_filter_clauses(filter_dto, user_sessions_table),
                access_ctx.as_where_clause(user_sessions_table),
            )
        )

        return result.rowcount == 1

    async def update_many(
        self,
        filter_dto: FilterManyUserSessionsDTO,
        update_dto: UpdateUserSessionDTO,
        access_ctx: AccessContext,
    ) -> int:
        """Обновляет данные множества пользовательских сессий.

        Parameters
        ----------
        filter_dto : FilterManyUserSessionsDTO
            Параметры фильтрации.
        update_dto : UpdateUserSessionDTO
            Новые данные пользовательских сессий.
        access_ctx : AccessContext
            Контекст доступа.

        Returns
        -------
        int
            Количество успешно обновлённых записей.
        """
        result = await self.connection.execute(
            update(user_sessions_table)
            .values(**update_dto.to_update_values())
            .where(
                *self._build_filter_clauses(filter_dto, user_sessions_table),
                access_ctx.as_where_clause(user_sessions_table),
            )
        )

        return result.rowcount

    async def delete_one(
        self, filter_dto: FilterOneUserSessionDTO, access_ctx: AccessContext
    ) -> bool:
        """Удаляет запись о пользовательской сессии из базы данных.

        Parameters
        ----------
        filter_dto : FilterOneNoteDTO
            Параметры фильтрации.
        access_ctx : AccessContext
            Контекст доступа.

        Returns
        -------
        bool
            True если сессия найдена и успешно удалена.
        """
        result = await self.connection.execute(
            delete(user_sessions_table).where(
                *self._build_filter_clauses(filter_dto, user_sessions_table),
                access_ctx.as_where_clause(user_sessions_table),
            )
        )

        return result.rowcount == 1

    async def delete_many(
        self, filter_dto: FilterManyUserSessionsDTO, access_ctx: AccessContext
    ) -> int:
        """Удаляет множество записей о пользовательских сессиях из базы данных.

        Parameters
        ----------
        filter_dto : FilterManyUserSessionsDTO
            Параметры фильтрации.
        access_ctx : AccessContext
            Контекст доступа.

        Returns
        -------
        int
            Количество успешно удалённых записей.
        """
        result = await self.connection.execute(
            delete(user_sessions_table).where(
                *self._build_filter_clauses(filter_dto, user_sessions_table),
                access_ctx.as_where_clause(user_sessions_table),
            )
        )

        return result.rowcount
