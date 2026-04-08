from typing import cast
from uuid import UUID

import redis.asyncio as redis

from app.config import get_settings
from app.core.enums import IdempotencyStatus
from app.core.types import TokenType
from app.schemas.dto.idempotency_key import IdempotencyKeyDTO

settings = get_settings()


class RedisClient:
    """Инфраструктурный клиент для работы с Redis.

    Предоставляет единый интерфейс для работы с Redis в рамках приложения:
    - blacklist токенов (revocation);
    - кэширование счётчиков;
    - идемпотентность;
    - другие вспомогательные механизмы.

    Несмотря на то, что клиент объединяет несколько доменов, каждая группа
    методов логически изолирована (token blacklist, counters, idempotency).
    При росте проекта может быть вынесена в отдельные сервисы/репозитории.

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
    get_count(scope, user_id)
        Возвращает закэшированное количество записей пользователя.
    set_count(scope, user_id, count, ttl)
        Устанавливает значение счётчика в кэше.
    increment_count(scope, user_id)
        Инкрементирует счётчик записей пользователя.
    decrement_count(scope, user_id)
        Декрементирует счётчик записей пользователя.
    acquire_idempotency_key(scope, user_id, key, ttl)
        Атомарно захватывает ключ идемпотентности.
    get_idempotency_state(scope, user_id, key)
        Возвращает текущее состояние ключа идемпотентности.
    finalize_idempotency_key(scope, user_id, key, ttl, response)
        Помечает ключ идемпотентности как завершённый.
    """

    def __init__(self, redis_url: str):
        self._redis_url = redis_url

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

    def _build_blacklist_key(self, jti: UUID, token_type: TokenType) -> str:
        """Формирует ключ для хранения информации об отозванном токене.

        Parameters
        ----------
        jti : UUID
            Уникальный идентификатор токена (JWT ID).
        token_type : TokenType
            Тип токена (access / refresh).

        Returns
        -------
        str
            Redis-ключ вида:
            "blacklist:{token_type}:{jti}"
        """
        return f"blacklist:{token_type}:{jti}"

    async def revoke_token(
        self,
        jti: UUID,
        ttl: int,
        token_type: TokenType = "access",
    ) -> None:
        """Добавляет токен в blacklist по его `jti`.

        Вместо хранения полного JWT-токена сохраняется только его идентификатор.
        Это снижает связность системы и повышает безопасность.

        TTL записи должен соответствовать оставшемуся времени жизни токена,
        чтобы Redis автоматически удалил запись после его истечения.

        Parameters
        ----------
        jti : UUID
            Уникальный идентификатор токена (JWT ID).
        ttl : int
            Оставшееся время жизни токена в секундах.
        token_type : TokenType
            Тип токена (access или refresh).
        """
        key = self._build_blacklist_key(jti, token_type)
        await self.client.setex(key, ttl, "1")

    async def is_token_revoked(
        self,
        jti: UUID,
        token_type: TokenType = "access",
    ) -> bool:
        """Проверяет, отозван ли токен.

        Токен считается недействительным, если его `jti` присутствует
        в Redis blacklist.

        Parameters
        ----------
        jti : UUID
            Уникальный идентификатор токена (JWT ID).
        token_type : TokenType
            Тип токена (access или refresh).

        Returns
        -------
        bool
            True, если токен отозван, иначе False.
        """
        key = self._build_blacklist_key(jti, token_type)
        return await self.client.exists(key) == 1

    async def restore_token(
        self,
        jti: UUID,
        token_type: TokenType = "access",
    ) -> None:
        """Удаляет токен из blacklist.

        Используется в редких сценариях:
        - rollback операций;
        - исправление ошибок отзыва токена;
        - тестирование.

        В нормальном процессе не требуется, так как TTL автоматически
        очищает записи.

        Parameters
        ----------
        jti : UUID
            Уникальный идентификатор токена (JWT ID).
        token_type : TokenType
            Тип токена (access или refresh).
        """
        key = self._build_blacklist_key(jti, token_type)
        await self.client.delete(key)

    @staticmethod
    def _count_key(scope: str, user_id: UUID) -> str:
        """Вспомогательный "приватный" метод формирования Redis-ключа счётчика.

        Принимает на вход необходимые аргументы и формирует
        из них уникальный ключ для хранения счётчика в Redis.

        Parameters
        ----------
        scope : str
            Область применения счётчика (идиоматично namespace).
            Например: "files", "notes".
        user_id : UUID
            UUID пользователя, которому принадлежит счётчик.

        Returns
        -------
        str
            Уникальный ключ для менеджмента счётчика в Redis.
        """
        return f"count:{scope}:{user_id}"

    async def get_count(self, scope: str, user_id: UUID) -> int | None:
        """Получение значения счётчика из кэша.

        Возвращает закэшированное количество записей для пользователя
        или None, если ключ отсутствует в Redis (cache miss).

        Parameters
        ----------
        scope : str
            Область применения счётчика (идиоматично namespace).
            Например: "files", "notes".
        user_id : UUID
            UUID пользователя, которому принадлежит счётчик.

        Returns
        -------
        int | None
            Закэшированное количество записей или None при cache miss.
        """
        value = await self.client.get(self._count_key(scope, user_id))

        return int(value) if value is not None else None

    async def set_count(self, scope: str, user_id: UUID, count: int, ttl: int) -> None:
        """Устанавливает значение счётчика в кэше.

        Сохраняет количество записей для пользователя в Redis.
        Используется для прогрева кэша после обращения к БД.

        Parameters
        ----------
        scope : str
            Область применения счётчика (идиоматично namespace).
            Например: "files", "notes".
        user_id : UUID
            UUID пользователя, которому принадлежит счётчик.
        count : int
            Количество записей для сохранения.
        ttl : int
            Время жизни ключа в секундах.
        """
        await self.client.setex(self._count_key(scope, user_id), ttl, count)

    async def increment_count(self, scope: str, user_id: UUID) -> None:
        """Инкрементирует счётчик записей пользователя.

        Атомарно увеличивает счётчик на единицу.
        Если ключ отсутствует в Redis, операция не выполняется,
        чтобы не создавать некорректный счётчик в обход БД.

        Parameters
        ----------
        scope : str
            Область применения счётчика (идиоматично namespace).
            Например: "files", "notes".
        user_id : UUID
            UUID пользователя, которому принадлежит счётчик.
        """
        redis_key = self._count_key(scope, user_id)

        if await self.client.exists(redis_key):
            await self.client.incr(redis_key)

    async def decrement_count(self, scope: str, user_id: UUID) -> None:
        """Декрементирует счётчик записей пользователя.

        Атомарно уменьшает счётчик на единицу.
        Если ключ отсутствует в Redis, операция не выполняется,
        чтобы не создавать некорректный счётчик в обход БД.
        Счётчик не может опуститься ниже нуля.

        Parameters
        ----------
        scope : str
            Область применения счётчика (идиоматично namespace).
            Например: "files", "notes".
        user_id : UUID
            UUID пользователя, которому принадлежит счётчик.
        """
        redis_key = self._count_key(scope, user_id)

        if await self.client.exists(redis_key):
            await self.client.decr(redis_key)

    @staticmethod
    def _idempotency_key(scope: str, user_id: UUID, key: UUID) -> str:
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
        False - если ключ уже существует.

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
        redis_key = self._idempotency_key(scope, user_id, key)

        created = await self.client.hsetnx(  # type: ignore
            redis_key,
            "status",
            IdempotencyStatus.PROCESSING,
        )

        if created:
            await self.client.hset(redis_key, "response", "")  # type: ignore
            await self.client.expire(redis_key, ttl)

        return cast(bool, created == 1)

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
        redis_key = self._idempotency_key(scope, user_id, key)

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
        redis_key = self._idempotency_key(scope, user_id, key)

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
