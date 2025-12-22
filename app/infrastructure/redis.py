from typing import Any, Self

import redis.asyncio as redis

from app.config import Settings, get_settings

settings: Settings = get_settings()


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
    revoke_token(token, ttl)
        Добавляет токен в черный список.
    is_token_revoked(token)
        Проверяет, находится ли токен в черном списке.
    delete_token(token)
        Удаление токена из черного списка.
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
