from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UserNotFoundException
from app.models.couple import CoupleModel
from app.models.user import UserModel
from app.repositories.interface import RepositoryInterface
from app.schemas.dto.user import CoupleDTO, PartnerDTO, UserDTO


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
    get_partner_by_user_id(user_id)
        Получение информации о партнёре пользователя.
    get_couple_by_partner_id(partner_id)
        Получение DTO пары по UUID одного из партнёров.
    register_couple(partner1_id, partner2_id)
        Регистрация пары между пользователями.
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
        self.session.add(
            UserModel(
                username=username,
                password_hash=password_hash,
            )
        )

    async def get_user_by_id(self, id_: UUID) -> UserDTO | None:
        """Возвращает DTO пользователя по его id.

        Parameters
        ----------
        id_ : UUID
            UUID пользователя.

        Returns
        -------
        UserDTO | None
            DTO записи пользователя, None - если пользователь с таким UUID не найден.
        """
        user: UserModel | None = await self._get_user_by_id(id_)

        return UserDTO.model_validate(user) if user else None

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

    async def get_user_by_username(self, username: str) -> UserDTO | None:
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
        user: UserModel | None = await self._get_user_by_username(username)

        return UserDTO.model_validate(user) if user else None

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

    async def get_partner_by_user_id(self, user_id: UUID) -> PartnerDTO | None:
        """Получение информации о партнёре пользователя.

        Получает UUID пользователя, проверяет его на существование,
        возвращает сохранённую информацию о партнёре этого пользователя.

        Parameters
        ----------
        user_id : UUID
            UUID пользователя в системе.

        Returns
        -------
        PartnerDTO | None
            Сохранённая о партнёре пользователя информация:
            - PartnerDTO если партнёр найден;
            - None если партнёр не найден.

        Raises
        ------
        UserNotFoundException
            Пользователь с таким UUID не найден.
        """
        user: UserModel | None = await self._get_user_by_id(user_id)

        if user is None:
            raise UserNotFoundException(detail=f"User with id={user_id} not found.")

        partner: UserModel | None = await user.get_partner()

        return PartnerDTO.model_validate(partner) if partner else None

    async def get_couple_by_partner_id(self, partner_id: UUID) -> CoupleDTO | None:
        """Получение DTO пары по UUID одного из партнёров.

        Получает на вход UUID одного из партнёров и ищет в базе данных
        запись о паре, в которой состоит данный пользователь.

        Parameters
        ----------
        partner_id : UUID
            UUID пользователя.

        Returns
        -------
        CoupleDTO | None
            DTO пары между пользователем и его партнёром, None - если пользователь не состоит в паре.
        """
        couple: CoupleModel | None = await self.session.scalar(
            select(CoupleModel).where(
                or_(
                    CoupleModel.partner1_id == partner_id,
                    CoupleModel.partner2_id == partner_id,
                ),
            )
        )

        return CoupleDTO.model_validate(couple) if couple else None

    async def register_couple(self, partner1_id: UUID, partner2_id: UUID) -> None:
        """Регистрация пары между пользователями.

        Добавляет в базу данных запись о новой паре между пользователями.

        Parameters
        ----------
        partner1_id : UUID
            UUID первого пользователя пары.
        partner2_id : UUID
            UUID второго пользователя пары.
        """
        self.session.add(
            CoupleModel(
                partner1_id=partner1_id,
                partner2_id=partner2_id,
            )
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

        Raises
        ------
        UserNotFoundException
            Пользователь с таким UUID не найден.
        """
        user: UserModel | None = await self._get_user_by_id(user_id)
        if user is None:
            raise UserNotFoundException(detail=f"User with id={user_id} not found.")

        user.refresh_token_hash = refresh_token_hash
