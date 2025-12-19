from typing import Annotated, Any, AsyncGenerator

from fastapi import Depends
from minio import Minio

from app.infrastructure.minio import minio_client
from app.infrastructure.postgresql import UnitOfWork
from app.infrastructure.redis import RedisClient


def get_minio_client() -> Minio:
    """Возвращает project-wide экземпляр клиента MinIO.

    Это соответствует best practices при работе с MinIO,
    а интеграция этого клиента в механизм FastAPI DI упрощает
    разработку и соответствует философии фреймворка.

    Returns
    -------
    Minio
        Project-wide инстанс клиента MinIO.
    """
    return minio_client


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


async def get_redis() -> AsyncGenerator[RedisClient, Any]:
    """Фабрика для создания зависимости Redis.

    Используется для автоматического менеджмента соединения с Redis.
    При входе в контекст (async with) создается новое соединение,
    при выходе — закрывается. Если в контексте возникнет исключение,
    оно будет проброшено дальше.

    Yields
    ------
    RedisClient
        Экземпляр клиента Redis.

    Notes
    -----
    При закрытии контекста (даже не в случае исключения или выхода из области видимости),
    соединение с Redis будет закрыто. Все дальнейшие запросы будут отклонены.
    """
    async with RedisClient() as redis:
        yield redis


MinioClientDependency = Annotated[Minio, Depends(get_minio_client)]
"""Зависимость на получение клиента MinIO."""

UnitOfWorkDependency = Annotated[UnitOfWork, Depends(get_unit_of_work)]
"""Зависимость на получение экземпляра Unit of Work в асинхронном контексте."""

RedisClientDependency = Annotated[RedisClient, Depends(get_redis)]
"""Зависимость на получение клиента Redis в асинхронном контексте."""
