from uuid import UUID

from app.infrastructure.postgresql import UnitOfWork
from app.repositories.users import UsersRepository
from app.schemas.dto.users import UserDTO, UserWithCredentialsDTO


class UsersService:
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
        super().__init__()

        self._user_repo: UsersRepository = unit_of_work.get_repository(UsersRepository)

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
        user: UserWithCredentialsDTO | None = await self._user_repo.get_user_by_id(
            user_id
        )

        if user is None:
            raise RuntimeError("Unknown error. Check access token validation path.")

        return UserDTO.model_validate(user)
