from datetime import datetime, timedelta, timezone
from math import ceil
from typing import Literal, overload
from uuid import uuid4

from jose import ExpiredSignatureError, JWTError
from pydantic import ValidationError

from app.config import Settings
from app.core.exceptions.auth import (
    IncorrectPasswordException,
    IncorrectUsernameOrPasswordException,
    InvalidTokenException,
    NewPasswordSameAsOldException,
    PasswordUpdateFailedException,
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
from app.core.types import TokenType
from app.infrastructure.postgresql import UnitOfWork
from app.infrastructure.redis import RedisClient
from app.repositories.couple_request import CoupleRequestRepository
from app.repositories.user import UserRepository
from app.repositories.user_session import UserSessionRepository
from app.schemas.dto.payload import (
    AccessTokenPayload,
    AnyTokenPayload,
    RefreshTokenPayload,
)
from app.schemas.dto.token import Tokens


class AuthService:
    """Сервис аутентификации и авторизации.

    Реализует бизнес-логику для:
    - регистрации и аутентификации пользователей;
    - генерации, валидации и обновления JWT;
    - управления пользовательскими сессиями и токенами.

    Использует:
    - PostgreSQL для хранения пользователей и сессий;
    - Redis для хранения отозванных access-токенов.

    Attributes
    ----------
    _redis_client : RedisClient
        Клиент для работы с Redis (blacklist access-токенов).
    _couple_request_repo : CoupleRequestRepository
        Репозиторий пар между пользователями.
    _user_repo : UserRepository
        Репозиторий пользователей.
    _user_session_repo : UserSessionRepository
        Репозиторий пользовательских сессий (refresh-токены).

    Methods
    -------
    register(username, password)
        Регистрирует пользователя.
    login(username, password)
        Аутентифицирует пользователя и создаёт новую сессию.
    refresh(refresh_token)
        Обновляет пару токенов (refresh rotation).
    logout(access_token)
        Завершает текущую сессию пользователя.
    change_password(current_password, new_password, access_token)
        Изменяет пароль пользователя и завершает сессию.
    validate_access_token(access_token)
        Проверяет валидность access-токена.
    """

    def __init__(
        self, unit_of_work: UnitOfWork, redis_client: RedisClient, settings: Settings
    ):
        self._redis_client = redis_client
        self._settings = settings

        self._couple_request_repo = unit_of_work.get_repository(CoupleRequestRepository)
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

        if user is None or not verify(password, user.password_hash):
            raise IncorrectUsernameOrPasswordException(
                detail="Incorrect username or password."
            )

        couple = await self._couple_request_repo.get_active_couple_by_partner_id(
            user.id
        )

        current_time = datetime.now(timezone.utc)
        expires_at = current_time + timedelta(
            days=self._settings.REFRESH_TOKEN_LIFETIME_DAYS
        )

        session_id = uuid4()

        refresh_token = create_jwt(
            user.id, current_time, exp=expires_at, session_id=session_id
        )

        await self._user_session_repo.add_user_session(
            session_id, user.id, hash_token(refresh_token), expires_at, current_time
        )

        return Tokens(
            access=create_jwt(
                user.id,
                current_time,
                expires_delta=timedelta(
                    minutes=self._settings.ACCESS_TOKEN_LIFETIME_MINUTES
                ),
                session_id=session_id,
                couple_id=couple.id if couple else None,
            ),
            refresh=refresh_token,
        )

    async def refresh(self, refresh_token: str | None) -> Tokens:
        """Обновляет пару токенов по валидному refresh-токену.

        Выполняет:
        - валидацию refresh-токена;
        - проверку существования сессии и совпадения хеша токена;
        - refresh rotation (инвалидация старого refresh-токена);
        - генерацию новой пары токенов.

        Parameters
        ----------
        refresh_token : str | None
            Refresh-токен из заголовка Authorization.

        Returns
        -------
        Tokens
            Новая пара access и refresh токенов.

        Raises
        ------
        TokenNotPassedException
            Токен обновления не передан в заголовках запроса.
        InvalidTokenException
            Токен невалиден или не соответствует активной сессии.
        """
        if refresh_token is None:
            raise TokenNotPassedException(
                detail="Refresh token not found in Authorization header. Make sure to add it with Bearer scheme.",
                token_type="refresh",
            )

        payload = self._validate_token(refresh_token, "refresh")

        couple = await self._couple_request_repo.get_active_couple_by_partner_id(
            payload.sub
        )

        current_time = datetime.now(timezone.utc)
        expires_at = current_time + timedelta(
            days=self._settings.REFRESH_TOKEN_LIFETIME_DAYS
        )

        new_refresh_token = create_jwt(
            payload.sub, current_time, exp=expires_at, session_id=payload.session_id
        )

        # атомарное обновление хэша токена обновления
        updated = (
            await self._user_session_repo.update_user_session_by_refresh_token_hash(
                hash_token(refresh_token),
                hash_token(new_refresh_token),
                expires_at,
                current_time,
            )
        )

        if not updated:
            raise InvalidTokenException(
                detail="There's no active session which token hash equals passed one's hash.",
                token_type="refresh",
            )

        return Tokens(
            access=create_jwt(
                payload.sub,
                current_time,
                expires_delta=timedelta(
                    minutes=self._settings.ACCESS_TOKEN_LIFETIME_MINUTES
                ),
                session_id=payload.session_id,
                couple_id=couple.id if couple else None,
            ),
            refresh=new_refresh_token,
        )

    async def _invalidate_token_and_session(
        self, access_token: str, payload: AnyTokenPayload
    ) -> None:
        """Отзывает access-токен и удаляет связанную пользовательскую сессию.

        Выполняет:
        - добавление access-токена в blacklist (Redis) до истечения срока жизни;
        - удаление пользовательской сессии по `session_id`.

        Parameters
        ----------
        access_token : str
            Валидный access-токен.
        payload : AnyTokenPayload
            Декодированный payload токена (обязательно содержит `exp` и `session_id`).

        Notes
        -----
        TTL для blacklist вычисляется на основе `exp` токена.

        Raises
        ------
        InvalidTokenException
            Если payload не содержит обязательных claims.
        """
        current_time = datetime.now(timezone.utc).timestamp()
        ttl = ceil(payload.exp.timestamp() - current_time)

        if ttl > 0:
            await self._redis_client.revoke_token(token=access_token, ttl=ttl)

        user_session = await self._user_session_repo.get_user_session_by_id(
            payload.session_id
        )

        if user_session is not None:
            await self._user_session_repo.delete_user_session_by_id(user_session.id)

    async def logout(self, access_token: str | None) -> None:
        """Завершает текущую сессию пользователя.

        Выполняет валидацию access-токена, отзыв токена (blacklist)
        и удаление связанной пользовательской сессии.

        Parameters
        ----------
        access_token : str | None
            Access-токен пользователя из заголовка Authorization.
        """
        payload = await self.validate_access_token(access_token)
        assert access_token is not None

        await self._invalidate_token_and_session(access_token, payload)

    async def change_password(
        self,
        current_password: str,
        new_password: str,
        access_token: str | None,
    ) -> None:
        """Изменяет пароль пользователя.

        Выполняет следующую последовательность действий:
        - Валидирует access-токен и извлекает payload;
        - Проверяет корректность текущего пароля;
        - Проверяет, что новый пароль отличается от текущего;
        - Обновляет хэш пароля в БД;
        - Инвалидирует текущий токен и сессию.

        Parameters
        ----------
        current_password : str
            Текущий пароль пользователя для подтверждения операции.
        new_password : str
            Новый пароль пользователя.
        access_token : str | None
            Access-токен, полученный из заголовков запроса.

        Raises
        ------
        IncorrectPasswordException
            Если текущий пароль введён неверно.
        NewPasswordSameAsOldException
            Если новый пароль совпадает с текущим.
        PasswordUpdateFailedException
            Если обновление пароля в БД не было применено.
        """
        payload = await self.validate_access_token(access_token)
        assert access_token is not None

        user = await self._user_repo.get_user_by_id(payload.sub)

        if user is None or not verify(current_password, user.password_hash):
            raise IncorrectPasswordException(detail="Current password is incorrect.")

        if verify(new_password, user.password_hash):
            raise NewPasswordSameAsOldException(
                detail="New password must differ from current."
            )

        updated = await self._user_repo.update_password_hash(
            payload.sub, hash_(new_password)
        )

        if not updated:
            raise PasswordUpdateFailedException(
                detail="Failed to update password: no rows were affected."
            )

        await self._invalidate_token_and_session(access_token, payload)

    async def validate_access_token(
        self, access_token: str | None
    ) -> AccessTokenPayload:
        """Проверяет валидность access-токена.

        Parameters
        ----------
        access_token : str | None
            Access-токен из заголовка Authorization.

        Returns
        -------
        AccessTokenPayload
            Декодированный payload токена.

        Raises
        ------
        TokenNotPassedException
            Токен не передан.
        TokenRevokedException
            Токен был отозван (находится в blacklist).
        InvalidTokenException
            Токен невалиден или повреждён.
        TokenSignatureExpiredException
            Срок действия токена истёк.
        """
        if access_token is None:
            raise TokenNotPassedException(
                detail="Access token not found in Authorization header. Make sure to add it with Bearer scheme.",
                token_type="access",
            )

        if await self._redis_client.is_token_revoked(access_token):
            raise TokenRevokedException(detail="Access token has been revoked.")

        return self._validate_token(access_token, "access")

    @overload
    @staticmethod
    def _validate_token(
        token: str, token_type: Literal["access"]
    ) -> AccessTokenPayload: ...

    @overload
    @staticmethod
    def _validate_token(
        token: str, token_type: Literal["refresh"]
    ) -> RefreshTokenPayload: ...

    @staticmethod
    def _validate_token(token: str, token_type: TokenType) -> AnyTokenPayload:
        """Валидирует JWT и возвращает его payload.

        Parameters
        ----------
        token : str
            JWT для валидации.
        token_type : TokenType
            Тип токена (access или refresh).

        Returns
        -------
        AnyTokenPayload
            Декодированный payload токена.

        Raises
        ------
        TokenSignatureExpiredException
            Срок действия токена истёк.
        InvalidTokenException
            Токен повреждён, некорректно подписан или содержит невалидный payload.
        """
        try:
            return jwt_decode(token, token_type)
        except ExpiredSignatureError:
            raise TokenSignatureExpiredException(
                detail="Signature of passed token has expired.",
                token_type=token_type,
            )
        except JWTError, ValidationError:
            raise InvalidTokenException(
                detail="The passed token is damaged or poorly signed.",
                token_type=token_type,
            )
