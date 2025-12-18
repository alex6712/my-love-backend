from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserModel
from app.core.exceptions import UserNotFoundException, UsernameAlreadyExistsException
from app.repositories.interface import RepositoryInterface
from app.schemas.dto.user import UserDTO


class UserRepository(RepositoryInterface):
    """Репозиторий пользователя.

    Реализация паттерна Репозиторий. Является объектом доступа к данным (DAO).
    Реализует основные CRUD операции с пользователями.

    Attributes
    ----------
    session : AsyncSession
        Объект асинхронной сессии запроса.

    Methods
    -------
    add_user(user_info)
        Добавляет в базу данных новую запись о пользователе.
    get_user_by_id(id_)
        Возвращает модель пользователя по его id.
    get_user_by_username(username)
        Возвращает модель пользователя по его username.
    update_refresh_token(user, refresh_token)
        Перезаписывает токен обновления пользователя.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def add_user(self, username: str, password_hash: str) -> None:
        """Добавляет в базу данных новую запись о пользователе.

        Parameters
        ----------
        username : str
            Имя пользователя приложения.
        password_hash : str
            Хеш пароля пользователя приложения.
        """
        if await self._get_user_by_username(username) is not None:
            raise UsernameAlreadyExistsException(
                detail=f"User with username={username} already exists.",
            )

        self.session.add(
            UserModel(
                username=username,
                password_hash=password_hash,
            )
        )

    async def get_user_by_id(self, id_: UUID) -> UserDTO:
        """Возвращает DTO пользователя по его id.

        Parameters
        ----------
        id_ : UUID
            UUID пользователя.

        Returns
        -------
        UserDTO
            DTO записи пользователя.
        """
        user: UserModel | None = await self.session.scalar(
            select(UserModel).where(UserModel.id == id_)
        )

        if user is None:
            raise UserNotFoundException(detail=f"User with id={id_} not found.")

        return UserDTO.model_validate(user)

    async def _get_user_by_id(self, id_: UUID) -> UserModel | None:
        """Возвращает модель пользователя по его id.

        Parameters
        ----------
        id_ : UUID
            UUID пользователя.

        Returns
        -------
        UserModel | None
            SQL модель записи пользователя, если пользователь не найден - None.
        """
        return await self.session.scalar(select(UserModel).where(UserModel.id == id_))

    async def get_user_by_username(self, username: str) -> UserDTO:
        """Возвращает DTO пользователя по его username.

        Parameters
        ----------
        username : str
            Логин пользователя, уникальное имя.

        Returns
        -------
        UserDTO
            DTO записи пользователя.
        """
        user: UserModel | None = await self.session.scalar(
            select(UserModel).where(UserModel.username == username)
        )

        if user is None:
            raise UserNotFoundException(
                detail=f"User with username={username} not found.",
            )

        return UserDTO.model_validate(user)

    async def _get_user_by_username(self, username: str) -> UserModel | None:
        """Возвращает модель пользователя по его username.

        Parameters
        ----------
        username : str
            Логин пользователя, уникальное имя.

        Returns
        -------
        UserModel | None
            SQL модель записи пользователя, если пользователь не найден - None.
        """
        return await self.session.scalar(
            select(UserModel).where(UserModel.username == username)
        )

    async def update_refresh_token_hash(
        self, user_id: UUID, refresh_token_hash: str | None
    ):
        """Перезаписывает токен обновления пользователя.

        Notes
        -----
        В этом случае используются функции SQLAlchemy ORM, которые позволяют
        изменить значение атрибута объекта записи пользователя,
        и при закрытии сессии эти изменения будут сохранены в базе данных.

        Parameters
        ----------
        user_id : UUID
            UUID пользователя, у которого необходимо изменить хеш токена.
        refresh_token_hash : str | None
            Новый токен обновления в хэшированном виде.
        """
        user: UserModel | None = await self._get_user_by_id(user_id)

        if user is None:
            raise UserNotFoundException(detail=f"User with id={user_id} not found.")

        user.refresh_token_hash = refresh_token_hash
