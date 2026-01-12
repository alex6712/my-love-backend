from typing import TYPE_CHECKING, Annotated, Any, AsyncGenerator

from fastapi import Depends

from app.infrastructure.postgresql import UnitOfWork
from app.infrastructure.redis import RedisClient, redis_client
from app.infrastructure.s3 import get_s3_client as _get_s3_client

if TYPE_CHECKING:
    from types_aiobotocore_s3 import S3Client


async def get_s3_client() -> AsyncGenerator["S3Client", None]:
    """Зависимость для получения асинхронного S3 клиента.

    Клиент автоматически закрывается после завершения запроса.

    Yields
    ------
    S3Client
        Асинхронный S3 клиент.
    """
    async with _get_s3_client() as client:
        yield client


async def get_unit_of_work() -> AsyncGenerator[UnitOfWork, Any]:
    """Создает уникальный объект асинхронного контекста транзакции.

    Используется для автоматической оркестрации репозиториями в сервисном слое:
    - по запросу конструирует требуемый репозиторий с внедрённой текущей сессией;
    - в автоматическом режиме выполняет `commit()` при успешной транзакции;
    - при любых исключениях выполняет `rollback()`,
      сохраняя таким образом атомарность операций с данными.

    Yields
    ------
    UnitOfWork
        Объект асинхронного контекста транзакции.
    """
    async with UnitOfWork() as uow:
        yield uow


def get_redis_client() -> RedisClient:
    """Возвращает project-wide экземпляр клиента Redis.

    Это соответствует best practices при работе с Redis,
    а интеграция этого клиента в механизм FastAPI DI упрощает
    разработку и соответствует философии фреймворка.

    Returns
    -------
    RedisClient
        Project-wide инстанс клиента Redis.
    """
    return redis_client


S3ClientDependency = Annotated["S3Client", Depends(get_s3_client)]
"""Зависимость на получение асинхронного S3 клиента."""

UnitOfWorkDependency = Annotated[UnitOfWork, Depends(get_unit_of_work)]
"""Зависимость на получение экземпляра Unit of Work в асинхронном контексте."""

RedisClientDependency = Annotated[RedisClient, Depends(get_redis_client)]
"""Зависимость на получение клиента Redis."""
