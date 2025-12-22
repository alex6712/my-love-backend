from datetime import datetime, timezone

from jose import ExpiredSignatureError, JWTError

from app.core.exceptions import (
    CredentialsException,
    TokenNotPassedException,
    TokenRevokedException,
    UsernameAlreadyExistsException,
    UserNotFoundException,
)
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
from app.repositories.user import UserRepository
from app.schemas.dto.user import UserDTO


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

    def __init__(self, unit_of_work: UnitOfWork, redis_client: RedisClient):
        super().__init__()

        self._redis_client: RedisClient = redis_client
        self._user_repo: UserRepository = unit_of_work.get_repository(UserRepository)

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
        if await self._user_repo.get_user_by_username(username) is not None:
            raise UsernameAlreadyExistsException(
                detail=f"User with username={username} already exists.",
            )

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
        user: UserDTO | None = await self._user_repo.get_user_by_username(username)

        if user is None:
            raise UserNotFoundException(
                detail=f"User with username={username} not found."
            )

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
            Токен обновления, полученный из headers.

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
            Хеш токена обновления из headers и хеш из БД не совпадают.
        """
        if refresh_token is None:
            raise TokenNotPassedException(
                detail="Refresh token is missing in headers.",
                token_type="refresh",
            )

        payload: Payload = await AuthService._validate_token(refresh_token)

        user: UserDTO | None = await self._user_repo.get_user_by_id(payload["sub"])

        if user is None:
            raise CredentialsException(
                detail="Unknown user: there's no user with such id.",
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

    async def logout(self, access_token: Token) -> None:
        """Выполняет выход пользователя из системы путем инвалидации JWT.

        Parameters
        ----------
        access_token : Token
            Валидный access токен пользователя, полученный при аутентификации.
            Должен содержать актуальный payload с идентификатором пользователя (sub).

        Returns
        -------
        None
            Метод не возвращает значение при успешном выполнении.

        Raises
        ------
        UserNotFoundException
            Возникает если пользователь, указанный в payload токена, не существует в системе.
        """
        payload: Payload = await self.validate_access_token(access_token)

        exp_timestamp: int | None = payload.get("exp")

        if exp_timestamp is None:
            raise CredentialsException(
                detail="Could not validate credentials.",
                credentials_type="token",
            )

        current_time = datetime.now(timezone.utc).timestamp()
        ttl = int(exp_timestamp - current_time)

        if ttl > 0:
            await self._redis_client.revoke_token(token=access_token, ttl=ttl)

        await self._user_repo.update_refresh_token_hash(payload["sub"], None)

    async def validate_access_token(self, access_token: Token | None) -> Payload:
        """Проверяет валидность access-токена.

        Parameters
        ----------
        access_token : Token | None
            Токен доступа, полученный из headers.

        Returns
        -------
        Payload
            Расшифрованные данные токена.

        Raises
        ------
        TokenNotPassedException
            Отсутствует токен обновления в headers.
        """
        if access_token is None:
            raise TokenNotPassedException(
                detail="Access token is missing in headers.",
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
        await self._user_repo.update_refresh_token_hash(
            user.id, hash_(tokens["refresh"])
        )

        return tokens
