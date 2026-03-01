from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserModel
from app.repositories.interface import RepositoryInterface
from app.schemas.dto.user import UserWithCredentialsDTO


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
    get_user_by_id(user_id)
        Возвращает модель пользователя по его id.
    user_exists_by_id(user_id)
        Проверка на существование пользователя по его UUID.
    get_user_by_username(username)
        Возвращает модель пользователя по его username.
    user_exists_by_username(username)
        Проверка на существование пользователя по его username.
    update_refresh_token(user, refresh_token)
        Перезаписывает токен обновления пользователя.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    def add_user(self, username: str, password_hash: str) -> None:
        """Добавляет в базу данных новую запись о пользователе.

        Parameters
        ----------
        username : str
            Имя пользователя приложения.
        password_hash : str
            Хэш пароля пользователя приложения.
        """
        self.session.add(
            UserModel(
                username=username,
                password_hash=password_hash,
            )
        )

    async def get_user_by_id(self, user_id: UUID) -> UserWithCredentialsDTO | None:
        """Возвращает DTO пользователя по его id.

        Parameters
        ----------
        user_id : UUID
            UUID пользователя.

        Returns
        -------
        UserDTO | None
            DTO записи пользователя, None - если пользователь с таким UUID не найден.
        """
        user = await self._get_user_by_id(user_id)

        return UserWithCredentialsDTO.model_validate(user) if user else None

    async def user_exists_by_id(self, user_id: UUID) -> bool:
        """Проверка на существование пользователя по его UUID.

        Получает на вход UUID пользователя, проверяет, существует ли такой
        пользователь в базе данных.

        Parameters
        ----------
        user_id : UUID
            UUID пользователя для проверки.

        Returns
        -------
        bool
            Результат проверки:
            - True если пользователь существует;
            - False если пользователь не найден.
        """
        return await self._get_user_by_id(user_id) is not None

    async def _get_user_by_id(self, user_id: UUID) -> UserModel | None:
        """Возвращает модель пользователя по его id.

        Parameters
        ----------
        user_id : UUID
            UUID пользователя.

        Returns
        -------
        UserModel | None
            SQL модель записи пользователя, если пользователь не найден - None.
        """
        return await self.session.scalar(
            select(UserModel).where(UserModel.id == user_id)
        )

    async def get_user_by_username(
        self, username: str
    ) -> UserWithCredentialsDTO | None:
        """Возвращает DTO пользователя по его username.

        Parameters
        ----------
        username : str
            Логин пользователя, уникальное имя.

        Returns
        -------
        UserDTO | None
            DTO записи пользователя, None - если пользователь не найден.
        """
        user = await self._get_user_by_username(username)

        return UserWithCredentialsDTO.model_validate(user) if user else None

    async def user_exists_by_username(self, username: str) -> bool:
        """Проверка на существование пользователя по его username.

        Получает на вход username пользователя, проверяет, существует ли такой
        пользователь в базе данных.

        Parameters
        ----------
        username : str
            username пользователя для проверки.

        Returns
        -------
        bool
            Результат проверки:
            - True если пользователь существует;
            - False если пользователь не найден.
        """
        return await self._get_user_by_username(username) is not None

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

        Parameters
        ----------
        user_id : UUID
            UUID пользователя, у которого необходимо изменить хеш токена.
        refresh_token_hash : str | None
            Новый токен обновления в хэшированном виде.
        """
        await self.session.execute(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(refresh_token_hash=refresh_token_hash)
        )
