from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import ExpiredSignatureError, JWTError

from app.config import Settings
from app.core.exceptions.auth import (
    IncorrectUsernameOrPasswordException,
    InvalidTokenException,
    TokenNotPassedException,
    TokenRevokedException,
    TokenSignatureExpiredException,
)
from app.core.exceptions.user import UsernameAlreadyExistsException
from app.core.security import (
    create_jwt,
    hash_,
    hash_token,
    jwt_decode,
    verify,
)
from app.core.types import Payload, Tokens, TokenType
from app.infrastructure.postgresql import UnitOfWork
from app.infrastructure.redis import RedisClient
from app.repositories.user import UserRepository
from app.repositories.user_session import UserSessionRepository


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
    _user_session_repo : UserSessionRepository
        Репозиторий для операций с сессиями пользователей.

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

    def __init__(
        self, unit_of_work: UnitOfWork, redis_client: RedisClient, settings: Settings
    ):
        self._redis_client = redis_client
        self._settings = settings

        self._user_repo = unit_of_work.get_repository(UserRepository)
        self._user_session_repo = unit_of_work.get_repository(UserSessionRepository)

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
        if await self._user_repo.user_exists_by_username(username):
            raise UsernameAlreadyExistsException(
                detail=f"User with username={username} already exists."
            )

        self._user_repo.add_user(username, hash_(password))

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
        IncorrectUsernameOrPasswordException
            Не найден пользователь или несовпадение пароля и его хеша в БД.
        """
        user = await self._user_repo.get_user_by_username(username)

        credentials_exception = IncorrectUsernameOrPasswordException(
            detail="Incorrect username or password."
        )

        if user is None:
            raise credentials_exception

        if not verify(password, user.password_hash):
            raise credentials_exception

        current_time = datetime.now(timezone.utc)
        expires_at = current_time + timedelta(
            days=self._settings.REFRESH_TOKEN_LIFETIME_DAYS
        )

        refresh_token = create_jwt(str(user.id), current_time, exp=expires_at)

        session_id = await self._user_session_repo.add_user_session(
            user.id, hash_token(refresh_token), expires_at, current_time
        )

        return {
            "access": create_jwt(
                # перевод UUID в строку, т.к. этот объект не сериализуется
                str(user.id),
                current_time,
                expires_delta=timedelta(
                    minutes=self._settings.ACCESS_TOKEN_LIFETIME_MINUTES
                ),
                session_id=str(session_id),
            ),
            "refresh": refresh_token,
        }

    async def refresh(self, refresh_token: str | None) -> Tokens:
        """Обновляет пару токенов по валидному refresh-токену.

        Выполняет следующую последовательность действий:
        - Проверяет валидность и соответствие токена в БД;
        - Генерирует новую пару токенов;
        - Обновляет хеш refresh-токена в БД (инвалидируя предыдущий).

        Parameters
        ----------
        refresh_token : str | None
            Токен обновления, полученный из headers.

        Returns
        -------
        Tokens
            Новая пара access и refresh токенов.

        Raises
        ------
        TokenNotPassedException
            Токен обновления не передан в заголовках запроса.
        InvalidTokenException
            Не найден пользователь или несовпадение токена обновления и его хеша в БД.
        """
        if refresh_token is None:
            raise TokenNotPassedException(
                detail="Refresh token not found in Authorization header. Make sure to add it with Bearer scheme.",
                token_type="refresh",
            )

        payload = self._validate_token(refresh_token, "refresh")

        current_time = datetime.now(timezone.utc)
        expires_at = current_time + timedelta(
            days=self._settings.REFRESH_TOKEN_LIFETIME_DAYS
        )

        new_refresh_token = create_jwt(payload["sub"], current_time, exp=expires_at)

        # атомарное обновление хэша токена обновления
        user_session_id = (
            await self._user_session_repo.update_user_session_by_refresh_token_hash(
                hash_token(refresh_token),
                hash_token(new_refresh_token),
                expires_at,
                current_time,
            )
        )

        if user_session_id is None:
            raise InvalidTokenException(
                detail="There's no active session which token hash equals passed one's hash.",
                token_type="refresh",
            )

        return {
            "access": create_jwt(
                payload["sub"],
                current_time,
                expires_delta=timedelta(
                    minutes=self._settings.ACCESS_TOKEN_LIFETIME_MINUTES
                ),
                session_id=str(user_session_id),
            ),
            "refresh": new_refresh_token,
        }

    async def logout(self, access_token: str | None) -> None:
        """Выполняет выход пользователя из системы путем инвалидации JWT.

        Parameters
        ----------
        access_token : str | None
            Валидный access токен пользователя, полученный при аутентификации.
            Должен содержать актуальный payload с идентификатором пользователя (sub).

        Returns
        -------
        None
            Метод не возвращает значение при успешном выполнении.

        Raises
        ------
        InvalidTokenException
            Возникает если подпись токена верна, но в payload нет ключа `exp`.
        """
        payload = await self.validate_access_token(access_token)

        assert access_token is not None

        if not all(payload.get(claim) for claim in ("exp", "session_id")):
            raise InvalidTokenException(
                detail="The passed token is damaged or poorly signed.",
                token_type="access",
            )

        current_time = datetime.now(timezone.utc).timestamp()
        ttl = int(payload["exp"] - current_time)

        if ttl > 0:
            await self._redis_client.revoke_token(token=access_token, ttl=ttl)

        user_session = await self._user_session_repo.get_user_session_by_id(
            UUID(payload["session_id"])
        )

        if user_session is not None:
            await self._user_session_repo.delete_user_session_by_id(user_session.id)

    async def validate_access_token(self, access_token: str | None) -> Payload:
        """Проверяет валидность access-токена.

        Parameters
        ----------
        access_token : srt
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

        return self._validate_token(access_token, "access")

    @staticmethod
    def _validate_token(token: str, token_type: TokenType) -> Payload:
        """Валидирует JWT (статический "приватный" метод).

        Parameters
        ----------
        token : str
            JWT для валидации.
        token_type : TokenType
            Тип обрабатываемого токена.

        Returns
        -------
        Payload
            Полезная нагрузка токена.

        Raises
        ------
        InvalidTokenException
            - Если не хватает хотя бы одной из обязательных claims в payload токена;
            - При любых иных ошибках JWT.
        TokenSignatureExpiredException
            Если подпись токена просрочена.
        """
        damaged = InvalidTokenException(
            detail="The passed token is damaged or poorly signed.",
            token_type=token_type,
        )

        try:
            payload = jwt_decode(token)

            if not all(payload.get(claim) for claim in ("sub", "iat", "exp", "jti")):
                raise damaged
        except ExpiredSignatureError:
            raise TokenSignatureExpiredException(
                detail="Signature of passed token has expired.",
                token_type=token_type,
            )
        except JWTError:
            raise damaged

        # перевод обратно из строки в объект UUID
        payload["sub"] = UUID(payload["sub"])

        return payload
