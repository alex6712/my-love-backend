from datetime import timedelta
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings, get_settings
from app.core.dependencies.infrastructure import get_redis_client, get_s3_client
from app.core.security import create_jwt_pair, hash_
from app.main import my_love_backend
from app.models.base import BaseModel
from app.models.user import UserModel

settings: Settings = get_settings()


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """HTTP-клиент для тестирования API эндпоинтов.

    Создаёт асинхронного клиента, который делает запросы
    к приложению через ASGITransport.

    Yields
    ------
    AsyncClient
        Клиент для выполнения HTTP-запросов к тестируемому приложению.
    """
    my_love_backend.dependency_overrides.update(
        {get_redis_client: lambda: mock_redis_client}
    )
    my_love_backend.dependency_overrides.update({get_s3_client: lambda: mock_s3_client})

    async with AsyncClient(
        transport=ASGITransport(app=my_love_backend),
        base_url=f"http://0.0.0.0:8000/{settings.CURRENT_API_PATH}",
    ) as client:
        yield client

    my_love_backend.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Создаёт тестовый движок SQLite in-memory.

    Используется для быстрых unit-тестов без реального PostgreSQL.

    Yields
    ------
    AsyncEngine
        Движок in-memory SQLite для тестирования приложения.
    """
    engine: AsyncEngine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=NullPool,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(async_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Сессия БД для unit-тестов с SQLite in-memory.

    Создаёт отдельную транзакцию для каждого теста на основе
    движка с подключением к in-memory SQLite.

    Yields
    ------
    AsyncSession
        Сессия in-memory тестовой базы данных.
    """
    async_session_maker = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> UserModel:
    """Создаёт тестового пользователя в базе данных.

    Пользователь создаётся с уникальным UUID и хешированным паролем.

    Returns
    -------
    UserModel
        Модель созданного пользователя.
    """
    user_id = uuid4()
    password = "test_password123"
    password_hash = hash_(password)

    user: UserModel = UserModel(
        id=user_id,
        username=f"test_user_{user_id.hex[:8]}",
        password_hash=password_hash,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest_asyncio.fixture
async def test_user_with_password(db_session: AsyncSession) -> tuple[UserModel, str]:
    """Создаёт тестового пользователя и возвращает его с паролем.

    Возвращает кортеж из модели пользователя и открытого пароля.
    Полезно для тестов логина, где нужно проверить верификацию пароля.

    Returns
    -------
    tuple[UserModel, str]
        Кортеж (пользователь, открытый пароль).
    """
    user_id = uuid4()
    password = "secure_password_123"
    password_hash = hash_(password)

    user: UserModel = UserModel(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        password_hash=password_hash,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user, password


@pytest.fixture
def auth_headers(test_user: UserModel) -> dict[str, str]:
    """Генерирует заголовки авторизации для тестового пользователя.

    Создаёт пару JWT-токенов (access + refresh) для пользователя
    и возвращает заголовок Authorization с Bearer-токеном.

    Parameters
    ----------
    test_user : UserModel
        Тестовый пользователь, для которого создаются токены.

    Returns
    -------
    dict[str, str]
        Заголовки с Authorization: Bearer <access_token>.
    """
    tokens = create_jwt_pair({"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {tokens['access']}"}


@pytest.fixture
def auth_headers_with_refresh(test_user: UserModel) -> dict[str, str]:
    """Генерирует заголовки с обоими токенами.

    Возвращает словарь с обоими токенами для тестов,
    требующих доступ к refresh-токену.

    Parameters
    ----------
    test_user : UserModel
        Тестовый пользователь.

    Returns
    -------
    dict[str, str]
        Словарь с 'Authorization' и 'X-Refresh-Token'.
    """
    tokens = create_jwt_pair({"sub": str(test_user.id)})
    return {
        "Authorization": f"Bearer {tokens['access']}",
        "X-Refresh-Token": tokens["refresh"],
    }


@pytest.fixture
def mock_redis_client() -> MagicMock:
    """Создаёт мок-клиент Redis для тестирования без реального Redis.

    Настраивает базовое поведение:
    - is_token_revoked возвращает False (токен не отозван)
    - revoke_token возвращает None

    Returns
    -------
    MagicMock
        Мок-объект RedisClient с настроенными методами.
    """
    mock = MagicMock()
    mock.is_token_revoked = AsyncMock(return_value=False)
    mock.revoke_token = AsyncMock(return_value=None)
    mock.delete_token = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def mock_s3_client() -> MagicMock:
    """Создаёт мок-клиент S3 для тестирования загрузки файлов.

    Настраивает базовое поведение для операций с S3:
    - upload_fileobj возвращает None
    - generate_presigned_url возвращает тестовую URL
    - head_object возвращает успешный ответ
    - delete_object возвращает None

    Returns
    -------
    MagicMock
        Мок-объект S3Client с настроенными методами.
    """
    mock = MagicMock()
    mock.upload_fileobj = AsyncMock(return_value=None)
    mock.generate_presigned_url = AsyncMock(
        return_value="https://minio.test/upload?signature=test"
    )
    mock.head_object = AsyncMock(return_value={"ContentLength": 1024})
    mock.delete_object = AsyncMock(return_value=None)
    return mock


@pytest_asyncio.fixture
async def created_test_user(db_session: AsyncSession) -> UserModel:
    """Создаёт пользователя с подтверждённым refresh-токеном.

    Используется для тестов, где нужно проверить логику с refresh-токеном.

    Returns
    -------
    UserModel
        Пользователь с установленным refresh_token_hash.
    """
    user_id = uuid4()
    password = "test_password"
    password_hash = hash_(password)
    refresh_hash = hash_("valid_refresh_token")

    user = UserModel(
        id=user_id,
        username=f"refresh_user_{user_id.hex[:8]}",
        password_hash=password_hash,
        refresh_token_hash=refresh_hash,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest.fixture
def expired_access_token(test_user: UserModel) -> str:
    """Генерирует просроченный access-токен для тестирования.

    Используется для тестов проверки истечения токена.

    Parameters
    ----------
    test_user : UserModel
        Пользователь для создания токена.

    Returns
    -------
    str
        JWT access-токен с истёкшим сроком действия.
    """
    tokens = create_jwt_pair(
        {"sub": str(test_user.id)},
        at_expires_delta=timedelta(seconds=-1),  # Уже истёк
    )
    return tokens["access"]


@pytest_asyncio.fixture
async def authenticated_client(
    app_with_mocks: FastAPI,
    auth_headers: dict[str, str],
) -> AsyncGenerator[AsyncClient, None]:
    """HTTP-клиент с авторизованным пользователем."""
    async with AsyncClient(
        transport=ASGITransport(app=app_with_mocks),
        base_url=f"http://0.0.0.0:8000/{settings.CURRENT_API_PATH}",
        headers=auth_headers,
    ) as client:
        yield client
