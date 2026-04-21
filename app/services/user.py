from uuid import UUID

from app.core.exceptions.base import NothingToUpdateException
from app.core.exceptions.user import UserNotFoundException
from app.infra.postgres.uow import UnitOfWork
from app.repositories.user import UserRepository
from app.schemas.dto.user import UpdateUserDTO, UserDTO


class UserService:
    """Сервис работы с пользователями.

    Реализует бизнес-логику для менеджмента пользователей
    и их данных профиля.

    Attributes
    ----------
    _user_repo : UserRepository
        Репозиторий для операций с пользователями в БД.

    Methods
    -------
    get_me(user_id)
        Получение информации о текущем пользователе.
    update_profile(patch_profile_dto, user_id)
        Частичное обновление атрибутов профиля пользователя по его UUID.
    """

    def __init__(self, unit_of_work: UnitOfWork):
        self._user_repo = unit_of_work.get_repository(UserRepository)

    async def get_me(self, user_id: UUID) -> UserDTO:
        """Получение информации о пользователе.

        Возвращает DTO пользователя по UUID из полученного токена
        доступа.

        Parameters
        ----------
        user_id : UUID
            UUID пользователя.

        Returns
        -------
        UserDTO
            Информация о текущем пользователе.
        """
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundException(f"User with id={user_id} not found.")

        return UserDTO.model_validate(user)

    async def update_profile(self, update_dto: UpdateUserDTO, user_id: UUID) -> None:
        """Частичное обновление атрибутов профиля пользователя по его UUID.

        Передаёт данные в репозиторий для обновления профиля пользователя.
        Обновляет только явно переданные поля (не равные `UNSET`).

        Parameters
        ----------
        update_dto : UpdateUserDTO
            DTO с полями для обновления. Содержит только явно переданные поля.
        user_id : UUID
            UUID пользователя, чей профиль требуется обновить.

        Raises
        ------
        NothingToUpdateException
            Не было передано ни одного поля на обновление.
        UserNotFoundException
            Если пользователь с указанным идентификатором не найден.
        """
        if update_dto.is_empty():
            raise NothingToUpdateException(detail="No fields provided for update.")

        if not await self._user_repo.update(user_id, update_dto):
            raise UserNotFoundException(f"User with id={user_id} not found.")
