from jose import ExpiredSignatureError, JWTError

from app.core.security import (
    Token,
    Tokens,
    Payload,
    create_jwt_pair,
    jwt_decode,
    hash_,
    verify,
)
from app.core.unit_of_work import UnitOfWork
from app.exceptions import (
    CredentialsException,
    TokenNotPassedException,
)
from app.repositories.user import UserRepository
from app.schemas.dto.user import UserDTO
from app.services.interface import ServiceInterface


class AuthService(ServiceInterface):
    """Сервис аутентификации и авторизации.

    Реализует бизнес-логику для:
    - Регистрации и аутентификации пользователей
    - Генерации, валидации и обновления JWT
    - Управления токенами в базе данных

    Attributes
    ----------
    unit_of_work : UnitOfWork
        Объект асинхронного контекста транзакции.
    _user_repo : UserRepository
        Репозиторий для операций с пользователями в БД.

    Methods
    -------
    login(form_data)
        Аутентифицирует пользователя по логину/паролю.
    refresh()
        Обновляет пару токенов по валидному refresh-токену.
    validate_access_token()
        Проверяет валидность access-токена.
    require_roles(required_roles)
        Проверяет наличие ролей у пользователя.
    _validate_token(token)
        Проверяет подпись токена.
    _get_jwt_pair(user)
        Генерирует новую пару JWT.
    """

    def __init__(self, unit_of_work: UnitOfWork):
        super().__init__(unit_of_work)

        self._user_repo: UserRepository = self.unit_of_work.get_repository(
            UserRepository
        )

    async def register(self, username: str, password: str) -> None:
        """Регистрирует пользователя в системе.

        Parameters
        ----------
        username : str
            Логин пользователя.
        password : str
            Пароль пользователя в открытом виде.

        Raises
        ------
        UsernameAlreadyExistsException
           Пользователь с переданным username уже существует.
        """
        await self._user_repo.add_user(username, hash_(password))

    async def login(self, username: str, password: str) -> Tokens:
        """Аутентифицирует пользователя и возвращает JWT.

        Parameters
        ----------
        username : str
            Логин пользователя.
        password : str
            Пароль пользователя в открытом виде.

        Returns
        -------
        Tokens
            Пара access и refresh токенов.

        Raises
        ------
        UserNotFoundException
            Не найден пользователь с переданным username.
        CredentialsException
            Несовпадение пароля и его хеша в БД.
        """
        user: UserDTO = await self._user_repo.get_user_by_username(username)

        if not verify(password, user.password_hash):
            raise CredentialsException(
                detail="The passed password and the hash from the database do not match.",
                credentials_type="password",
            )

        return await self._get_new_jwt_pair(user)

    async def refresh(self, refresh_token: Token | None) -> Tokens:
        """Обновляет пару токенов по валидному refresh-токену.

        - Проверяет валидность и соответствие токена в БД;
        - Генерирует новую пару токенов;
        - Обновляет хеш refresh-токена в БД (инвалидируя предыдущий).

        Parameters
        ----------
        refresh_token : Token | None
            Токен обновления, полученный из cookies.

        Returns
        -------
        Tokens
            Новая пара access и refresh токенов.

        Raises
        ------
        TokenNotPassedException
            Отсутствует refresh-токен.
        UserNotFoundException
            Пользователь с user_id из токена не найден в БД.
        CredentialsException
            Хеш токена обновления из cookies и хеш из БД не совпадают.
        """
        if refresh_token is None:
            raise TokenNotPassedException(
                detail="Refresh token is missing in cookies.",
                token_type="refresh",
            )

        payload: Payload = await AuthService._validate_token(refresh_token)

        user: UserDTO = await self._user_repo.get_user_by_id(payload["sub"])

        credentials_exception: CredentialsException = CredentialsException(
            detail="The passed refresh token and the hash from the database do not match.",
            credentials_type="token",
        )

        if user.refresh_token_hash is None:
            raise credentials_exception

        if not verify(refresh_token, user.refresh_token_hash):
            raise credentials_exception

        return await self._get_new_jwt_pair(user)

    async def logout(self, access_token: Token) -> None:
        """Выполняет выход пользователя из системы путем инвалидации refresh токена.

        Parameters
        ----------
        access_token : Token
            Валидный JWT access токен пользователя, полученный при аутентификации.
            Должен содержать актуальный payload с идентификатором пользователя (sub).

        Returns
        -------
        None
            Метод не возвращает значение при успешном выполнении.

        Raises
        ------
        TokenNotPassedException
            Отсутствует токен обновления в cookies.
        UserNotFoundException
            Возникает если пользователь, указанный в payload токена, не существует в системе.
        """
        payload: Payload = await AuthService._validate_token(access_token)

        user: UserDTO = await self._user_repo.get_user_by_id(payload["sub"])

        await self._user_repo.update_refresh_token_hash(user, None)

    async def validate_access_token(self, access_token: Token | None) -> Payload:
        """Проверяет валидность access-токена.

        Parameters
        ----------
        access_token : Token | None
            Токен доступа, полученный из cookies.

        Returns
        -------
        Payload
            Расшифрованные данные токена.

        Raises
        ------
        TokenNotPassedException
            Отсутствует токен обновления в cookies.
        """
        if access_token is None:
            raise TokenNotPassedException(
                detail="Access token is missing in cookies.",
                token_type="access",
            )

        return await AuthService._validate_token(access_token)

    @staticmethod
    async def _validate_token(token: str) -> Payload:
        """Валидирует JWT (статический "приватный" метод).

        Parameters
        ----------
        token : str
            JWT для валидации.

        Returns
        -------
        Payload
            Полезная нагрузка токена.

        Raises
        ------
        CredentialsException
            - Если нет "sub" в payload токена;
            - Если подпись токена просрочена;
            - При любых иных ошибках JWT.
        """
        try:
            if (payload := jwt_decode(token)).get("sub") is None:
                raise CredentialsException(
                    detail='There is no "sub" in token payload.',
                    credentials_type="token",
                )
        except ExpiredSignatureError:
            raise CredentialsException(
                detail="Signature has expired.",
                credentials_type="token",
            )
        except JWTError:
            raise CredentialsException(
                detail="Could not validate credentials.",
                credentials_type="token",
            )

        return payload

    async def _get_new_jwt_pair(self, user: UserDTO) -> Tokens:
        """Генерирует новую пару JWT и обновляет данные в БД ("приватный" метод).

        Parameters
        ----------
        user : UserDTO
            Объект пользователя.

        Returns
        -------
        Tokens
            Сгенерированная пара токенов.

        Raises
        ------
        HTTPException
            400: Ошибка целостности данных при обновлении БД.

        Notes
        -----
        Обязательное поле в payload: {"sub": username}
        """
        tokens: Tokens = create_jwt_pair(
            {
                "sub": str(user.id),
                "name": user.username,
            }
        )
        await self._user_repo.update_refresh_token_hash(user, hash_(tokens["refresh"]))

        return tokens
