from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.auth import (
    IncorrectUsernameOrPasswordException,
    InvalidTokenException,
    TokenNotPassedException,
    TokenRevokedException,
)
from app.core.exceptions.user import UsernameAlreadyExistsException
from app.core.security import create_jwt_pair, hash_
from app.infrastructure.postgresql import UnitOfWork
from app.services.auth import AuthService


class TestAuthServiceRegister:
    """Тесты метода register сервиса AuthService."""

    @pytest.mark.asyncio
    async def test_register_success(
        self, db_session: AsyncSession, mock_redis_client: MagicMock
    ):
        """Успешная регистрация нового пользователя."""
        uow = MagicMock(spec=UnitOfWork)
        uow.session = db_session

        mock_repo = MagicMock()
        uow.get_repository = MagicMock(return_value=mock_repo)
        mock_repo.user_exists_by_username = AsyncMock(return_value=False)
        mock_repo.add_user = MagicMock()

        auth_service = AuthService(uow, mock_redis_client)

        await auth_service.register("new_user", "secure_password")

        mock_repo.user_exists_by_username.assert_called_once_with("new_user")
        mock_repo.add_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_duplicate_username(
        self, db_session: AsyncSession, mock_redis_client: MagicMock
    ):
        """Регистрация с существующим username должна вызывать исключение."""
        uow = MagicMock(spec=UnitOfWork)
        uow.session = db_session

        mock_repo = MagicMock()
        uow.get_repository = MagicMock(return_value=mock_repo)
        mock_repo.user_exists_by_username = AsyncMock(return_value=True)

        auth_service = AuthService(uow, mock_redis_client)

        with pytest.raises(UsernameAlreadyExistsException):
            await auth_service.register("existing_user", "password123")

        mock_repo.add_user.assert_not_called()


class TestAuthServiceLogin:
    """Тесты метода login сервиса AuthService."""

    @pytest.mark.asyncio
    async def test_login_success(
        self, db_session: AsyncSession, mock_redis_client: MagicMock
    ):
        """Успешный вход возвращает пару токенов."""
        uow = MagicMock(spec=UnitOfWork)
        uow.session = db_session

        user_id = uuid4()
        password = "test_password"
        password_hash = hash_(password)

        user_dto = MagicMock()
        user_dto.id = user_id
        user_dto.password_hash = password_hash

        mock_repo = MagicMock()
        uow.get_repository = MagicMock(return_value=mock_repo)
        mock_repo.get_user_by_username = AsyncMock(return_value=user_dto)
        mock_repo.update_refresh_token_hash = AsyncMock()

        auth_service = AuthService(uow, mock_redis_client)

        tokens = await auth_service.login("test_user", password)

        assert "access" in tokens
        assert "refresh" in tokens
        mock_repo.update_refresh_token_hash.assert_called_once()

    @pytest.mark.asyncio
    async def test_login_user_not_found(
        self, db_session: AsyncSession, mock_redis_client: MagicMock
    ):
        """Вход с несуществующим пользователем вызывает исключение."""
        uow = MagicMock(spec=UnitOfWork)
        uow.session = db_session

        mock_repo = MagicMock()
        uow.get_repository = MagicMock(return_value=mock_repo)
        mock_repo.get_user_by_username = AsyncMock(return_value=None)

        auth_service = AuthService(uow, mock_redis_client)

        with pytest.raises(IncorrectUsernameOrPasswordException):
            await auth_service.login("nonexistent", "password")

    @pytest.mark.asyncio
    async def test_login_wrong_password(
        self, db_session: AsyncSession, mock_redis_client: MagicMock
    ):
        """Вход с неправильным паролем вызывает исключение."""
        uow = MagicMock(spec=UnitOfWork)
        uow.session = db_session

        user_id = uuid4()
        correct_password = "correct_password"
        wrong_password = "wrong_password"
        password_hash = hash_(correct_password)

        user_dto = MagicMock()
        user_dto.id = user_id
        user_dto.password_hash = password_hash

        mock_repo = MagicMock()
        uow.get_repository = MagicMock(return_value=mock_repo)
        mock_repo.get_user_by_username = AsyncMock(return_value=user_dto)

        auth_service = AuthService(uow, mock_redis_client)

        with pytest.raises(IncorrectUsernameOrPasswordException):
            await auth_service.login("test_user", wrong_password)


class TestAuthServiceRefresh:
    """Тесты метода refresh сервиса AuthService."""

    @pytest.mark.asyncio
    async def test_refresh_success(
        self, db_session: AsyncSession, mock_redis_client: MagicMock
    ):
        """Успешное обновление токенов."""
        from app.core.security import create_jwt

        uow = MagicMock(spec=UnitOfWork)
        uow.session = db_session

        user_id = uuid4()
        refresh_token_payload = {"sub": str(user_id)}
        refresh_token = create_jwt(
            refresh_token_payload, expires_delta=timedelta(days=7)
        )
        refresh_hash = hash_(refresh_token)

        user_dto = MagicMock()
        user_dto.id = user_id
        user_dto.password_hash = "some_hash"
        user_dto.refresh_token_hash = refresh_hash

        mock_repo = MagicMock()
        uow.get_repository = MagicMock(return_value=mock_repo)
        mock_repo.get_user_by_id = AsyncMock(return_value=user_dto)
        mock_repo.update_refresh_token_hash = AsyncMock()

        auth_service = AuthService(uow, mock_redis_client)

        tokens = await auth_service.refresh(refresh_token)

        assert "access" in tokens
        assert "refresh" in tokens
        mock_repo.update_refresh_token_hash.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_token_not_passed(
        self, db_session: AsyncSession, mock_redis_client: MagicMock
    ):
        """Обновление без токена вызывает исключение."""
        uow = MagicMock(spec=UnitOfWork)
        uow.session = db_session

        auth_service = AuthService(uow, mock_redis_client)

        with pytest.raises(TokenNotPassedException):
            await auth_service.refresh(None)

    @pytest.mark.asyncio
    async def test_refresh_user_not_found(
        self, db_session: AsyncSession, mock_redis_client: MagicMock
    ):
        """Обновление для несуществующего пользователя."""
        uow = MagicMock(spec=UnitOfWork)
        uow.session = db_session

        mock_repo = MagicMock()
        uow.get_repository = MagicMock(return_value=mock_repo)
        mock_repo.get_user_by_id = AsyncMock(return_value=None)

        auth_service = AuthService(uow, mock_redis_client)

        with pytest.raises(InvalidTokenException):
            await auth_service.refresh("some_token")

    @pytest.mark.asyncio
    async def test_refresh_wrong_token_hash(
        self, db_session: AsyncSession, mock_redis_client: MagicMock
    ):
        """Обновление с неправильным хешем токена."""
        uow = MagicMock(spec=UnitOfWork)
        uow.session = db_session

        user_id = uuid4()
        stored_hash = hash_("stored_token")
        wrong_token = "wrong_token"

        user_dto = MagicMock()
        user_dto.id = user_id
        user_dto.password_hash = "hash"
        user_dto.refresh_token_hash = stored_hash

        mock_repo = MagicMock()
        uow.get_repository = MagicMock(return_value=mock_repo)
        mock_repo.get_user_by_id = AsyncMock(return_value=user_dto)

        auth_service = AuthService(uow, mock_redis_client)

        with pytest.raises(InvalidTokenException):
            await auth_service.refresh(wrong_token)


class TestAuthServiceLogout:
    """Тесты метода logout сервиса AuthService."""

    @pytest.mark.asyncio
    async def test_logout_success(
        self, db_session: AsyncSession, mock_redis_client: MagicMock
    ):
        """Успешный выход инвалидирует токен."""
        uow = MagicMock(spec=UnitOfWork)
        uow.session = db_session

        user_id = uuid4()
        access_token = create_jwt_pair({"sub": str(user_id)})["access"]

        mock_repo = MagicMock()
        uow.get_repository = MagicMock(return_value=mock_repo)
        mock_repo.update_refresh_token_hash = AsyncMock()

        auth_service = AuthService(uow, mock_redis_client)

        await auth_service.logout(access_token)

        mock_redis_client.revoke_token.assert_called_once()
        mock_repo.update_refresh_token_hash.assert_called_once_with(user_id, None)

    @pytest.mark.asyncio
    async def test_logout_token_not_passed(
        self, db_session: AsyncSession, mock_redis_client: MagicMock
    ):
        """Выход без токена вызывает исключение."""
        uow = MagicMock(spec=UnitOfWork)
        uow.session = db_session

        auth_service = AuthService(uow, mock_redis_client)

        with pytest.raises(TokenNotPassedException):
            await auth_service.logout(None)


class TestAuthServiceValidateAccessToken:
    """Тесты метода validate_access_token сервиса AuthService."""

    @pytest.mark.asyncio
    async def test_validate_valid_token(
        self, db_session: AsyncSession, mock_redis_client: MagicMock
    ):
        """Валидация валидного токена возвращает payload."""
        uow = MagicMock(spec=UnitOfWork)
        uow.session = db_session

        user_id = uuid4()
        access_token = create_jwt_pair({"sub": str(user_id)})["access"]

        mock_redis_client.is_token_revoked = AsyncMock(return_value=False)

        auth_service = AuthService(uow, mock_redis_client)

        payload = await auth_service.validate_access_token(access_token)

        assert payload["sub"] == user_id

    @pytest.mark.asyncio
    async def test_validate_revoked_token(
        self, db_session: AsyncSession, mock_redis_client: MagicMock
    ):
        """Валидация отозванного токена вызывает исключение."""
        uow = MagicMock(spec=UnitOfWork)
        uow.session = db_session

        user_id = uuid4()
        access_token = create_jwt_pair({"sub": str(user_id)})["access"]

        mock_redis_client.is_token_revoked = AsyncMock(return_value=True)

        auth_service = AuthService(uow, mock_redis_client)

        with pytest.raises(TokenRevokedException):
            await auth_service.validate_access_token(access_token)

    @pytest.mark.asyncio
    async def test_validate_token_not_passed(
        self, db_session: AsyncSession, mock_redis_client: MagicMock
    ):
        """Валидация без токена вызывает исключение."""
        uow = MagicMock(spec=UnitOfWork)
        uow.session = db_session

        auth_service = AuthService(uow, mock_redis_client)

        with pytest.raises(TokenNotPassedException):
            await auth_service.validate_access_token(None)
