from uuid import UUID

from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError

from app.core.exceptions.user import UsernameAlreadyExistsException
from app.infra.postgres import get_constraint_name
from app.infra.postgres.tables.users import users_table
from app.repositories.interface import (
    CreateMixin,
    FilteredReadOneMixin,
    ReadOneMixin,
    RepositoryInterfaceNew,
    UpdateMixin,
)
from app.schemas.dto.user import (
    CreateUserDTO,
    FilterUserDTO,
    UpdateUserDTO,
    UserWithCredentialsDTO,
)


class UserRepository(
    RepositoryInterfaceNew,
    ReadOneMixin[UserWithCredentialsDTO],
    FilteredReadOneMixin[FilterUserDTO, UserWithCredentialsDTO],
    CreateMixin[CreateUserDTO, UserWithCredentialsDTO],
    UpdateMixin[UpdateUserDTO, UserWithCredentialsDTO],
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
    create(create_dto)
        Добавляет в базу данных новую запись о пользователе.
    get_one(record_id)
        Возвращает DTO пользователя по его id.
    get_one_filtered(filter_do)
        Возвращает DTO пользователя по фильтру.
    update(record_id, update_dto)
        Обновляет данные пользователя по его идентификатору.
    """

    async def create(self, create_dto: CreateUserDTO) -> UserWithCredentialsDTO:
        """Добавляет в базу данных новую запись о пользователе.

        Parameters
        ----------
        create_dto : CreateUserDTO
            Необходимые для создания записи данные о пользователе.

        Returns
        -------
        UserWithCredentialsDTO
            Доменное DTO пользователя с чувствительными данными.

        Raises
        ------
        UsernameAlreadyExistsException
           Пользователь с переданным username уже существует.
        """
        try:
            result = await self.connection.execute(
                insert(users_table)
                .values(**create_dto.to_create_values())
                .returning(users_table)
            )
        except IntegrityError as e:
            constraint = get_constraint_name(e)

            if constraint == "uq_users_username":
                raise UsernameAlreadyExistsException(
                    detail=f"User with username={create_dto.username} already exists."
                ) from e

            raise

        return UserWithCredentialsDTO.model_validate(result.mappings().one())

    async def get_one(self, record_id: UUID) -> UserWithCredentialsDTO | None:
        """Возвращает DTO пользователя по его id.

        Parameters
        ----------
        record_id : UUID
            UUID пользователя.

        Returns
        -------
        UserWithCredentialsDTO | None
            DTO записи пользователя, None - если пользователь с таким UUID не найден.
        """
        result = await self.connection.execute(
            select(users_table).where(users_table.c.id == record_id)
        )

        if not (row := result.mappings().first()):
            return None

        return UserWithCredentialsDTO.model_validate(row)

    async def get_one_filtered(
        self, filter_dto: FilterUserDTO
    ) -> UserWithCredentialsDTO | None:
        """Возвращает DTO пользователя по переданному фильтру.

        Parameters
        ----------
        filter_dto : FilterUserDTO
            Параметры фильтрации.

        Returns
        -------
        UserWithCredentialsDTO | None
            DTO записи пользователя, None - если пользователь не найден.
        """
        result = await self.connection.execute(
            select(users_table).where(
                *[
                    getattr(users_table.c, field) == value
                    for field, value in filter_dto.to_filter_values().items()
                ]
            )
        )

        if not (row := result.mappings().first()):
            return None

        return UserWithCredentialsDTO.model_validate(row)

    async def update(
        self, record_id: UUID, update_dto: UpdateUserDTO
    ) -> UserWithCredentialsDTO | None:
        """Обновляет данные пользователя по его идентификатору.

        Parameters
        ----------
        record_id : UUID
            Идентификатор обновляемого пользователя.
        update_dto : UpdateUserDTO
            Новые данные пользователя.

        Returns
        -------
        UserWithCredentialsDTO | None
            DTO обновлённого пользователя или None, если пользователь не найден.
        """
        result = await self.connection.execute(
            update(users_table)
            .where(users_table.c.id == record_id)
            .values(**update_dto.to_update_values())
            .returning(users_table)
        )

        if not (row := result.mappings().first()):
            return None

        return UserWithCredentialsDTO.model_validate(row)
