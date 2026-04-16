from uuid import UUID

from sqlalchemy import select, update

from app.models.user import UserModel
from app.repositories.interface import RepositoryInterface
from app.schemas.dto.user import PatchProfileDTO, UserWithCredentialsDTO


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
    update_password_hash(user_id, password_hash)
        Обновляет хэш пароля пользователя по его идентификатору.
    """

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

    async def update_password_hash(self, user_id: UUID, password_hash: str) -> bool:
        """Обновляет хэш пароля пользователя по его идентификатору.

        Выполняет обновление поля password_hash для указанного пользователя.
        Если пользователь с переданным идентификатором не найден, обновление не происходит.

        Parameters
        ----------
        user_id : UUID
            Уникальный идентификатор пользователя.

        password_hash : str
            Новый хэш пароля пользователя.

        Returns
        -------
        bool
            True, если пароль был успешно обновлён, иначе False.
        """
        updated = await self.session.scalar(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(password_hash=password_hash)
            .returning(UserModel.id)
        )

        return updated is not None

    async def update_user_by_id(
        self, patch_profile_dto: PatchProfileDTO, user_id: UUID
    ) -> bool:
        """Обновление атрибутов профиля пользователя в базе данных.

        Выполняет SQL-запрос UPDATE для изменения атрибутов профиля
        пользователя, фильтруя записи по идентификатору пользователя.

        Parameters
        ----------
        patch_profile_dto : PatchProfileDTO
            DTO с полями для обновления. Только явно переданные поля
            попадают в SET-часть запроса через `to_update_values()`.
        user_id : UUID
            UUID пользователя, чей профиль требуется обновить.

        Returns
        -------
        bool
            True, если запись была обновлена, False - если пользователь
            с указанным идентификатором не найден.
        """
        updated = await self.session.scalar(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(**patch_profile_dto.to_update_values())
            .returning(UserModel.id)
        )

        return updated is not None
