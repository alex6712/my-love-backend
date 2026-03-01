from uuid import UUID

from app.core.exceptions.user import UserNotFoundException
from app.infrastructure.postgresql import UnitOfWork
from app.repositories.user import UserRepository
from app.schemas.dto.user import UserDTO


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
        user = await self._user_repo.get_user_by_id(user_id)

        if user is None:
            raise UserNotFoundException(f"User with id={user_id} not found.")

        return UserDTO.model_validate(user)
