from datetime import datetime, timezone
from uuid import UUID

from jose import ExpiredSignatureError, JWTError

from app.core.exceptions.auth import (
    CredentialsException,
    TokenNotPassedException,
    TokenRevokedException,
)
from app.core.exceptions.user import UsernameAlreadyExistsException
from app.core.security import (
    Payload,
    Token,
    Tokens,
    create_jwt_pair,
    hash_,
    jwt_decode,
    verify,
)
from app.infrastructure.postgresql import UnitOfWork
from app.infrastructure.redis import RedisClient
from app.repositories.users import UsersRepository
from app.schemas.dto.users import UserWithCredentialsDTO


class AuthService:
    """Сервис аутентификации и авторизации.

    Реализует бизнес-логику для:
    - Регистрации и аутентификации пользователей;
    - Генерации, валидации и обновления JWT;
    - Управления токенами в базе данных.

    Attributes
    ----------
    _redis_client : RedisClient
        Клиент для работы с Redis.
    _user_repo : UserRepository
        Репозиторий для операций с пользователями в БД.

    Methods
    -------
    register(username, password)
        Регистрирует пользователя в системе.
    login(username, password)
        Аутентифицирует пользователя по логину/паролю.
    refresh(refresh_token)
        Обновляет пару токенов по валидному refresh-токену.
    logout(access_token)
        Выполняет выход пользователя из системы путем инвалидации JWT.
    validate_access_token(access_token)
        Проверяет валидность access-токена.
    _validate_token(token)
        Проверяет подпись токена.
    _get_jwt_pair(user)
        Генерирует новую пару JWT.
    """

    def __init__(self, unit_of_work: UnitOfWork, redis_client: RedisClient):
        super().__init__()

        self._redis_client: RedisClient = redis_client
        self._users_repo: UsersRepository = unit_of_work.get_repository(UsersRepository)

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
        if await self._users_repo.user_exists_by_username(username):
            raise UsernameAlreadyExistsException(
                detail=f"User with username={username} already exists."
            )

        await self._users_repo.add_user(username, hash_(password))

    async def login(self, username: str, password: str) -> Tokens:
        """Аутентифицирует пользователя и возвращает JWT.

        Проверяет существование пользователя по переданному `username`,
        сверяет хеш переданного пароля и сохранённый в базе данных
        хеш.

        Если все проверки пройдены успешно, возвращает пару JWT.

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
        CredentialsException
            Не найден пользователь или несовпадение пароля и его хеша в БД.
        """
        user: (
            UserWithCredentialsDTO | None
        ) = await self._users_repo.get_user_by_username(username)

        credentials_exception: CredentialsException = CredentialsException(
            detail="Incorrect username or password.",
            credentials_type="password",
        )

        if user is None:
            raise credentials_exception

        if not verify(password, user.password_hash):
            raise credentials_exception

        return await self._get_new_jwt_pair(user)

    async def refresh(self, refresh_token: Token | None) -> Tokens:
        """Обновляет пару токенов по валидному refresh-токену.

        Выполняет следующую последовательность действий:
        - Проверяет валидность и соответствие токена в БД;
        - Генерирует новую пару токенов;
        - Обновляет хеш refresh-токена в БД (инвалидируя предыдущий).

        Parameters
        ----------
        refresh_token : Token | None
            Токен обновления, полученный из headers.

        Returns
        -------
        Tokens
            Новая пара access и refresh токенов.

        Raises
        ------
        TokenNotPassedException
            Токен обновления не передан в заголовках запроса.
        CredentialsException
            Не найден пользователь или несовпадение токена обновления и его хеша в БД.
        """
        if refresh_token is None:
            raise TokenNotPassedException(
                detail="Refresh token not found in Authorization header. Make sure to add it with Bearer scheme.",
                token_type="refresh",
            )

        payload: Payload = await AuthService._validate_token(refresh_token)

        user: UserWithCredentialsDTO | None = await self._users_repo.get_user_by_id(
            payload["sub"]
        )

        if user is None:
            raise CredentialsException(
                detail="The passed token is damaged or poorly signed.",
                credentials_type="token",
            )

        credentials_exception: CredentialsException = CredentialsException(
            detail="The passed refresh token and the hash from the database do not match.",
            credentials_type="token",
        )

        if user.refresh_token_hash is None:
            raise credentials_exception

        if not verify(refresh_token, user.refresh_token_hash):
            raise credentials_exception

        return await self._get_new_jwt_pair(user)

    async def logout(self, access_token: Token | None) -> None:
        """Выполняет выход пользователя из системы путем инвалидации JWT.

        Parameters
        ----------
        access_token : Token | None
            Валидный access токен пользователя, полученный при аутентификации.
            Должен содержать актуальный payload с идентификатором пользователя (sub).

        Returns
        -------
        None
            Метод не возвращает значение при успешном выполнении.

        Raises
        ------
        CredentialsException
            Возникает если подпись токена верна, но в payload нет ключа `exp`.
        """
        payload: Payload = await self.validate_access_token(access_token)

        exp_timestamp: int | None = payload.get("exp")

        if exp_timestamp is None:
            raise CredentialsException(
                detail="The passed token is damaged or poorly signed.",
                credentials_type="token",
            )

        current_time = datetime.now(timezone.utc).timestamp()
        ttl = int(exp_timestamp - current_time)

        if ttl > 0:
            await self._redis_client.revoke_token(token=access_token, ttl=ttl)  # type: ignore

        await self._users_repo.update_refresh_token_hash(payload["sub"], None)

    async def validate_access_token(self, access_token: Token | None) -> Payload:
        """Проверяет валидность access-токена.

        Parameters
        ----------
        access_token : Token
            Токен доступа, полученный из headers.

        Returns
        -------
        Payload
            Расшифрованные данные токена.

        Raises
        ------
        TokenNotPassedException
            Токен доступа не передан в заголовках запроса.
        TokenRevokedException
            Переданный токен доступа был отозван.
        """
        if access_token is None:
            raise TokenNotPassedException(
                detail="Access token not found in Authorization header. Make sure to add it with Bearer scheme.",
                token_type="access",
            )

        if await self._redis_client.is_token_revoked(access_token):
            raise TokenRevokedException(detail="Access token has been revoked.")

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
        damaged: CredentialsException = CredentialsException(
            detail="The passed token is damaged or poorly signed.",
            credentials_type="token",
        )

        try:
            payload: Payload = jwt_decode(token)

            if not all(payload.get(name) for name in ("sub", "iat", "exp")):
                raise damaged
        except ExpiredSignatureError:
            raise CredentialsException(
                detail="Signature of passed token has expired.",
                credentials_type="token",
            )
        except JWTError:
            raise damaged

        # перевод обратно из строки в объект UUID (см. _get_new_jwt_pair)
        payload["sub"] = UUID(payload["sub"])

        return payload

    async def _get_new_jwt_pair(self, user: UserWithCredentialsDTO) -> Tokens:
        """Генерирует новую пару JWT и обновляет данные в БД ("приватный" метод).

        Parameters
        ----------
        user : UserDTO
            Объект пользователя.

        Returns
        -------
        Tokens
            Сгенерированная пара токенов.

        Notes
        -----
        Обязательное поле в payload: {"sub": user_id}
        """
        tokens: Tokens = create_jwt_pair(
            {
                # перевод UUID в строку, т.к. этот объект не сериализуется
                "sub": str(user.id),
            }
        )

        await self._users_repo.update_refresh_token_hash(
            user.id, hash_(tokens["refresh"])
        )

        return tokens
