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
from app.core.security import (
    create_jwt,
    hash_,
    hash_token,
    jwt_decode,
    verify,
)
from app.core.types import TokenType
from app.infra.postgres.uow import UnitOfWork
from app.infra.redis import RedisClient
from app.repositories.couple import CoupleRepository
from app.repositories.interface import PublicAccessContext
from app.repositories.user import UserRepository
from app.repositories.user_session import UserSessionRepository
from app.schemas.dto.auth import Tokens
from app.schemas.dto.payload import (
    AccessTokenPayload,
    AnyTokenPayload,
    RefreshTokenPayload,
)
from app.schemas.dto.user import CreateUserDTO, FilterOneUserDTO, UpdateUserDTO
from app.schemas.dto.user_session import (
    CreateUserSessionDTO,
    FilterManyUserSessionsDTO,
    FilterOneUserSessionDTO,
    UpdateUserSessionDTO,
)


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
    _couple_repo : CoupleRepository
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
        Обновляет пару токенов по refresh-токену.
    logout(access_token)
        Завершает текущую сессию пользователя.
    change_password(current_password, new_password, access_token)
        Изменяет пароль пользователя и завершает сессию.
    validate_access_token(access_token)
        Проверяет валидность access-токена.
    """

    def __init__(self, uow: UnitOfWork, redis_client: RedisClient, settings: Settings):
        self._redis_client = redis_client
        self._settings = settings

        self._couple_repo = uow.get_repository(CoupleRepository)
        self._user_repo = uow.get_repository(UserRepository)
        self._user_session_repo = uow.get_repository(UserSessionRepository)

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
        await self._user_repo.create_one(
            CreateUserDTO(username=username, password_hash=hash_(password))
        )

    async def login(self, username: str, password: str) -> Tokens:
        """Аутентифицирует пользователя и возвращает пару JWT.

        Проверяет существование пользователя по переданному `username`,
        сверяет хеш переданного пароля и сохранённый в базе данных
        хеш.

        При успешной аутентификации создаёт новую сессию и возвращает
        пару JWT-токенов: access (короткоживущий, для заголовка
        Authorization) и refresh (долгоживущий, для HttpOnly-cookie).

        Parameters
        ----------
        username : str
            Логин пользователя.
        password : str
            Пароль пользователя в открытом виде.

        Returns
        -------
        Tokens
            Пара JWT-токенов: access и refresh.

        Raises
        ------
        IncorrectUsernameOrPasswordException
            Не найден пользователь или несовпадение пароля и его хеша в БД.
        """
        user = await self._user_repo.read_one(
            FilterOneUserDTO(username=username), PublicAccessContext()
        )

        if user is None or not verify(password, user.password_hash):
            raise IncorrectUsernameOrPasswordException(
                detail="Incorrect username or password."
            )

        current_time = datetime.now(timezone.utc)
        expires_at = current_time + timedelta(
            days=self._settings.REFRESH_TOKEN_LIFETIME_DAYS
        )

        refresh_token = create_jwt(
            user.id,
            current_time,
            session_id := uuid4(),
            token_type="refresh",
            exp=expires_at,
        )

        await self._user_session_repo.create_one(
            CreateUserSessionDTO(
                id=session_id,
                user_id=user.id,
                refresh_token_hash=hash_token(refresh_token),
                expires_at=expires_at,
                last_used_at=current_time,
            )
        )

        return Tokens(
            access=create_jwt(
                user.id,
                current_time,
                session_id,
                token_type="access",
                expires_delta=timedelta(
                    minutes=self._settings.ACCESS_TOKEN_LIFETIME_MINUTES
                ),
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

        Вызывается из HTTP-эндпоинта `/auth/refresh`.

        Parameters
        ----------
        refresh_token : str | None
            Refresh-токен, извлечённый из HttpOnly-cookie.

        Returns
        -------
        Tokens
            Новая пара access и refresh токенов.

        Raises
        ------
        TokenNotPassedException
            Токен обновления не передан в cookie запроса.
        InvalidTokenException
            Токен невалиден или не соответствует активной сессии.
        TokenSignatureExpiredException
            Срок действия refresh-токена истёк.
        """
        if refresh_token is None:
            raise TokenNotPassedException(
                detail="Refresh token not found in auth cookie.", token_type="refresh"
            )

        payload = self._validate_token(refresh_token, "refresh")

        current_time = datetime.now(timezone.utc)
        expires_at = current_time + timedelta(
            days=self._settings.REFRESH_TOKEN_LIFETIME_DAYS
        )

        new_refresh_token = create_jwt(
            payload.sub,
            current_time,
            payload.sid,
            token_type="refresh",
            exp=expires_at,
        )

        # атомарное обновление хэша токена обновления
        updated = await self._user_session_repo.update_one(
            FilterOneUserSessionDTO(refresh_token_hash=hash_token(refresh_token)),
            UpdateUserSessionDTO(
                refresh_token_hash=hash_token(new_refresh_token),
                expires_at=expires_at,
                last_used_at=current_time,
            ),
            PublicAccessContext(),
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
                payload.sid,
                token_type="access",
                expires_delta=timedelta(
                    minutes=self._settings.ACCESS_TOKEN_LIFETIME_MINUTES
                ),
            ),
            refresh=new_refresh_token,
        )

    async def logout(self, payload: AccessTokenPayload) -> None:
        """Завершает текущую сессию пользователя.

        Выполняет отзыв токена (blacklist)
        и удаление связанной пользовательской сессии.

        Parameters
        ----------
        payload : AccessTokenPayload
            Полезная нагрузка (payload) access-токена текущего пользователя.
        """
        current_ts = datetime.now(timezone.utc).timestamp()
        ttl = ceil(payload.exp.timestamp() - current_ts)

        if ttl > 0:
            await self._redis_client.revoke_token(
                jti=payload.jti, ttl=ttl, token_type="access"
            )

        await self._user_session_repo.delete_one(
            FilterOneUserSessionDTO(id=payload.sid), PublicAccessContext()
        )

    async def change_password(
        self, current_password: str, new_password: str, payload: AccessTokenPayload
    ) -> None:
        """Изменяет пароль пользователя.

        Выполняет следующую последовательность действий:
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
        user = await self._user_repo.read_one_for_update(
            FilterOneUserDTO(id=payload.sub), PublicAccessContext()
        )

        if user is None or not verify(current_password, user.password_hash):
            raise IncorrectPasswordException(detail="Current password is incorrect.")

        if verify(new_password, user.password_hash):
            raise NewPasswordSameAsOldException(
                detail="New password must differ from current."
            )

        if not await self._user_repo.update_one(
            FilterOneUserDTO(id=payload.sub),
            UpdateUserDTO(password_hash=hash_(new_password)),
            PublicAccessContext(),
        ):
            raise PasswordUpdateFailedException(
                detail="Failed to update password: no rows were affected."
            )

        await self._user_session_repo.delete_many(
            FilterManyUserSessionsDTO(user_ids=[payload.sub]), PublicAccessContext()
        )

    async def validate_access_token(
        self, access_token: str | None
    ) -> AccessTokenPayload:
        """Проверяет валидность access-токена.

        Parameters
        ----------
        access_token : str | None
            Access-токен, извлечённый из заголовка
            `Authorization: Bearer <token>`.

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
                detail=(
                    "Access token is missing. Provide it in the "
                    "Authorization: Bearer <token> header."
                ),
                token_type="access",
            )

        payload = self._validate_token(access_token, "access")

        if await self._redis_client.is_token_revoked(payload.jti):
            raise TokenRevokedException(detail="Access token has been revoked.")

        return payload

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
