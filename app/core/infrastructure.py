from typing import Any, cast, Self, TypeVar

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings, get_settings
from app.core.exceptions import UnitOfWorkContextClosedException
from app.repositories.interface import RepositoryInterface

T = TypeVar("T", bound=RepositoryInterface)

settings: Settings = get_settings()

engine: AsyncEngine = create_async_engine(
    url=settings.POSTGRES_DSN,
    echo=False,
    pool_pre_ping=True,
)
AsyncSessionMaker: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


class UnitOfWork:
    """Единица работы (Unit of Work) для управления транзакцией и репозиториями.

    Класс инкапсулирует работу с асинхронной сессией SQLAlchemy, обеспечивает
    атомарность операций (commit/rollback) и управление жизненным циклом репозиториев.

    Parameters
    ----------
    session_maker : async_sessionmaker[AsyncSession]
        Фабрика асинхронных сессий SQLAlchemy. По умолчанию используется
        глобальный `AsyncSessionMaker`.

    Attributes
    ----------
    session : AsyncSession
        Текущая асинхронная сессия. Доступна только в пределах контекста
        (`async with UnitOfWork(): ...`).
    _repos : dict[type[RepositoryInterface], RepositoryInterface]
        Кэш созданных репозиториев для повторного использования в пределах
        одной транзакции.

    Raises
    ------
    UnitOfWorkContextClosedException
        Если попытаться получить доступ к сессии вне контекстного менеджера.
    """

    def __init__(
        self, session_maker: async_sessionmaker[AsyncSession] = AsyncSessionMaker
    ):
        self.session_maker = session_maker
        self._session: AsyncSession | None = None

        self._repos: dict[type[RepositoryInterface], RepositoryInterface] = {}

    @property
    def session(self) -> AsyncSession:
        if self._session is None:
            raise UnitOfWorkContextClosedException()

        return self._session

    async def __aenter__(self) -> Self:
        """Вход в асинхронный контекст.

        Создаёт новую асинхронную сессию и возвращает объект `UnitOfWork`.

        Returns
        -------
        UnitOfWork
            Текущий экземпляр `UnitOfWork`.
        """
        self._session = self.session_maker()
        return self

    async def __aexit__(self, exc_type: Any, *_: Any) -> None:
        """Выход из асинхронного контекста.

        В случае возникновения ошибки выполняется `rollback`, иначе — `commit`.
        После завершения сессия закрывается, а все кэшированные репозитории очищаются.

        Parameters
        ----------
        exc_type : Any
            Тип исключения, если оно возникло.
        """
        try:
            if exc_type is not None:
                await self.session.rollback()
            else:
                await self.session.commit()
        finally:
            await self.session.close()

            self._session = None
            self._repos.clear()

    def get_repository(self, repo_type: type[T]) -> T:
        """Получить экземпляр репозитория для работы с базой данных.

        Если репозиторий указанного типа ещё не был создан, он будет
        инициализирован с текущей сессией и сохранён в кэше.

        Parameters
        ----------
        repo_type : type[T]
            Класс репозитория, реализующий интерфейс `RepositoryInterface`.

        Returns
        -------
        T
            Экземпляр репозитория, связанный с текущей сессией.
        """
        if repo_type not in self._repos:
            self._repos[repo_type] = repo_type(self.session)

        return cast(T, self._repos[repo_type])


class RedisClient:
    """Клиент для работы с Redis.

    Создаёт пул подключений, из которого можно получить клиент Redis,
    и предоставляет методы для работы с ним.

    Attributes
    ----------
    _pool : redis.ConnectionPool | None
        Пул подключений Redis.

    Methods
    -------
    connect()
        Создание пула подключений.
    disconnect()
        Закрытие пула подключений.
    client()
        Получение клиента Redis из пула подключений.
    revoke_token(token: str, ttl: int)
        Добавляет токен в черный список.
    """

    def __init__(self):
        self._pool: redis.ConnectionPool | None = None

    async def connect(self) -> None:
        """Создание пула подключений.

        Подключается к Redis и создает пул подключений.

        Raises
        ------
        RuntimeError
            Если подключение уже было установлено
        """
        self._pool = redis.ConnectionPool.from_url(  # type: ignore
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=10,
        )

    async def disconnect(self) -> None:
        """Закрытие пула подключений.

        Закрывает пул подключений, если он был создан.
        Это также приводит к закрытию всех подключений в пуле.
        """
        if self._pool:
            await self._pool.disconnect()

    async def __aenter__(self) -> Self:
        """Вход в асинхронный контекст.

        Возвращает текущий экземпляр `RedisClient`,
        если подключение уже было установлено.
        Если нет, то создает новое подключение и возвращает его.

        Returns
        -------
        RedisClient
            Текущий экземпляр `RedisClient`.
        """
        if not self._pool:
            await self.connect()
            return self
        else:
            raise RuntimeError("Redis connection pool is already initialized.")

    async def __aexit__(self, *_: Any) -> None:
        """Выход из асинхронного контекста.

        Закрывает подключение к Redis. Если подключение не было установлено, ничего не делает.
        """
        await self.disconnect()

    @property
    def client(self) -> redis.Redis:
        """Получение клиента Redis из пула подключений.

        Returns
        -------
        redis.Redis
            Клиент Redis, подключенный к пулу подключений.
            Если пул не был создан, выбрасывает исключение RuntimeError.

        Raises
        ------
        RuntimeError
            Если подключение не было установлено
            или пул не был создан.
        """
        if not self._pool:
            raise RuntimeError("Redis connection pool is not initialized")

        return redis.Redis(connection_pool=self._pool)

    async def revoke_token(self, token: str, ttl: int) -> None:
        """Добавляет токен в черный список.

        Добавляет токен в Redis с ключом "blacklist:access_token:{token}",
        где {token} - это сам токен. Тем самым делая токен недействительным.

        Parameters
        ----------
        token : str
            Токен, который нужно добавить в черный список.
        ttl : int
            Время жизни токена в секундах.

        Returns
        -------
        None
            Токен добавлен в черный список.
        """
        await self.client.setex(f"blacklist:access_token:{token}", ttl, "1")

    async def is_token_revoked(self, token: str) -> bool:
        """Проверяет, находится ли токен в черном списке.

        Проверяет, находится ли токен в Redis с ключом "blacklist:access_token:{token}",
        где {token} - это сам токен. Если токен найден, то он считается недействительным.

        Parameters
        ----------
        token : str
            Токен, который нужно проверить.

        Returns
        -------
        bool
            True, если токен находится в черном списке, иначе False.
        """
        return await self.client.exists(f"blacklist:access_token:{token}") == 1

    async def delete_token(self, token: str) -> None:
        """Удаление токена из черного списка.

        Удаляет токен из Redis с ключом "blacklist:access_token:{token}",
        где {token} - это сам токен.

        Parameters
        ----------
        token : str
            Токен, который нужно удалить из черного списка.
        """
        await self.client.delete(f"blacklist:access_token:{token}")
