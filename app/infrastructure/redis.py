from uuid import UUID

import redis.asyncio as redis

from app.config import Settings, get_settings
from app.core.enums import IdempotencyStatus
from app.schemas.dto.idempotency_key import IdempotencyKeyDTO

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

    def __init__(self, redis_url: str):
        self._redis_url: str = redis_url

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
            self._redis_url,
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
            Оставшееся время жизни токена в секундах.

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

    def _idempotency_key(self, scope: str, user_id: UUID, key: UUID) -> str:
        """Вспомогательный "приватный" метод формирования Redis-ключа.

        Принимает на вход необходимые аргументы и формирует
        из них уникальный ключ для записи значений в Redis.

        Parameters
        ----------
        scope : str
            Область применения ключа (идиоматично namespace).
        user_id : UUID
            UUID пользователя, выполняющего операцию.
        key : UUID
            Значение ключа идемпотентности.

        Returns
        -------
        str
            Уникальный ключ для менеджмента значений в Redis.
        """
        return f"idempotency:{scope}:{user_id}:{key}"

    async def acquire_idempotency_key(
        self, scope: str, user_id: UUID, key: UUID, ttl: int
    ) -> bool:
        """Пытается атомарно захватить ключ идемпотентности.

        Возвращает True, если ключ был установлен впервые.
        False — если ключ уже существует.

        Parameters
        ----------
        scope : str
            Область применения ключа (идиоматично namespace).
        user_id : UUID
            UUID пользователя, выполняющего операцию.
        key : UUID
            Значения ключа идемпотентности.
        ttl : int
            Время жизни ключа в секундах.

        Returns
        -------
        bool
            Текущее состояние ключа идемпотентности.
        """
        redis_key: str = self._idempotency_key(scope, user_id, key)

        created: bool = (  # type: ignore
            await self.client.hsetnx(  # type: ignore
                redis_key,
                "status",
                IdempotencyStatus.PROCESSING,
            )
            == 1
        )

        if created:
            await self.client.hset(redis_key, "response", "")  # type: ignore
            await self.client.expire(redis_key, ttl)

        return created  # type: ignore

    async def get_idempotency_state(
        self, scope: str, user_id: UUID, key: UUID
    ) -> IdempotencyKeyDTO:
        """Получение текущего статуса идемпотентности.

        Возвращает текущее состояние идемпотентного ключа
        или None, если ключ отсутствует.

        Parameters
        ----------
        scope : str
            Область применения ключа (идиоматично namespace).
        user_id : UUID
            UUID пользователя, выполняющего операцию.
        key : UUID
            Значения ключа идемпотентности.

        Returns
        -------
        IdempotencyKeyDTO
            Текущий статус идемпотентности по ключу.
        """
        redis_key: str = self._idempotency_key(scope, user_id, key)

        data: dict[str, str] = await self.client.hgetall(redis_key)  # type: ignore

        return IdempotencyKeyDTO.model_validate(data)

    async def finalize_idempotency_key(
        self,
        scope: str,
        user_id: UUID,
        key: UUID,
        ttl: int,
        response: str | None = None,
    ) -> None:
        """Помечает идемпотентный ключ как завершённый.

        Перезаписывает значение ключа, изменяя статус запроса на завершённый
        и сохраняет результат операции.

        Parameters
        ----------
        scope : str
            Область применения ключа (идиоматично namespace).
        user_id : UUID
            UUID пользователя, выполняющего операцию.
        key : UUID
            Значения ключа идемпотентности.
        ttl : int
            Время жизни ключа в секундах.
        response : str | None
            Текст ответа от сервера.
        """
        redis_key: str = self._idempotency_key(scope, user_id, key)

        if response is None:
            response = ""

        await self.client.hset(  # type: ignore
            redis_key,
            mapping={
                "status": IdempotencyStatus.DONE,
                "response": response,
            },
        )
        await self.client.expire(redis_key, ttl)


redis_client: RedisClient = RedisClient(
    redis_url=settings.REDIS_URL.unicode_string(),
)
"""Project-wide клиент Redis, предоставляющий методы работы с хранилищем."""
