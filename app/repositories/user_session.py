from uuid import UUID

from sqlalchemy import delete, insert, select, update

from app.infra.postgres.tables.user_sessions import user_sessions_table
from app.repositories.interface import (
    CreateMixin,
    DeleteMixin,
    FilteredUpdateMixin,
    ReadOneMixin,
    RepositoryInterfaceNew,
)
from app.schemas.dto.user_session import (
    CreateUserSessionDTO,
    FilterUserSessionDTO,
    UpdateUserSessionDTO,
    UserSessionDTO,
)


class UserSessionRepository(
    RepositoryInterfaceNew,
    CreateMixin[CreateUserSessionDTO, UserSessionDTO],
    ReadOneMixin[UserSessionDTO],
    FilteredUpdateMixin[FilterUserSessionDTO, UpdateUserSessionDTO, UserSessionDTO],
    DeleteMixin[UserSessionDTO],
):
    """Репозиторий для управления пользовательскими сессиями.

    Реализует CRUD-операции над таблицей пользовательских сессий
    через SQLAlchemy AsyncSession.

    Methods
    -------
    create(create_dto)
        Создаёт новую пользовательскую сессию.
    get_one(record_id)
        Возвращает DTO пользовательской сессии по её идентификатору.
    update_by_refresh_token_hash(refresh_token_hash, update_dto)
        Обновляет данные сессии по хэшу токена обновления.
    delete(record_id)
        Удаляет сессию по её идентификатору.
    """

    async def create(self, create_dto: CreateUserSessionDTO) -> UserSessionDTO:
        """Создаёт новую пользовательскую сессию.

        Parameters
        ----------
        create_dto : CreateUserSessionDTO
            Необходимые для создания записи данные о сессии.

        Returns
        -------
        UserSessionDTO
            Доменное DTO пользовательской сессии.
        """
        result = await self.connection.execute(
            insert(user_sessions_table)
            .values(**create_dto.to_create_values())
            .returning(user_sessions_table)
        )

        return UserSessionDTO.model_validate(result.mappings().one())

    async def get_one(self, record_id: UUID) -> UserSessionDTO | None:
        """Возвращает DTO пользовательской сессии по её идентификатору.

        Parameters
        ----------
        record_id : UUID
            Идентификатор пользовательской сессии.

        Returns
        -------
        UserSessionDTO | None
            Доменное DTO записи сессии, None - если сессия с таким UUID не найдена.
        """
        result = await self.connection.execute(
            select(user_sessions_table).where(user_sessions_table.c.id == record_id)
        )

        if not (row := result.mappings().first()):
            return None

        return UserSessionDTO.model_validate(row)

    async def update_filtered(
        self,
        filter_dto: FilterUserSessionDTO,
        update_dto: UpdateUserSessionDTO,
    ) -> UserSessionDTO | None:
        """Обновляет данные сессии по хэшу токена обновления.

        Используется при ротации refresh-токена - заменяет хэш токена,
        обновляет время истечения и последнего использования сессии.

        Parameters
        ----------
        old_refresh_token_hash : str
            Хэш текущего refresh-токена, по которому ищется сессия.
        new_refresh_token_hash : str
            Хэш нового refresh-токена, который заменит старый.
        expires_at : datetime
            Новое время истечения сессии.
        last_used_at : datetime
            Время последнего использования сессии.

        Returns
        -------
        bool
            `True` если сессия найдена и обновлена, `False` если сессия
            с переданным хэшем не существует или уже неактивна.
        """
        result = await self.connection.execute(
            update(user_sessions_table)
            .where(
                *[
                    getattr(user_sessions_table.c, field) == value
                    for field, value in filter_dto.to_filter_values().items()
                ]
            )
            .values(**update_dto.to_update_values())
            .returning(user_sessions_table)
        )

        if not (row := result.mappings().first()):
            return None

        return UserSessionDTO.model_validate(row)

    async def delete(self, record_id: UUID) -> UserSessionDTO | None:
        """Удаляет сессию по её идентификатору.

        Parameters
        ----------
        record_id : UUID
            Идентификатор удаляемой сессии.

        Returns
        -------
        UserSessionDTO | None
            Доменное DTO удалённой записи сессии,
            None - если сессия с таким UUID не найдена.
        """
        result = await self.connection.execute(
            delete(user_sessions_table)
            .where(user_sessions_table.c.id == record_id)
            .returning(user_sessions_table)
        )

        if not (row := result.mappings().first()):
            return None

        return UserSessionDTO.model_validate(row)
