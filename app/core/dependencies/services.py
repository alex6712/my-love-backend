from typing import Annotated

from fastapi import Depends

from app.core.dependencies.infrastructure import (
    UnitOfWorkDependency,
    RedisClientDependency,
)
from app.services.auth import AuthService


def get_auth_service(
    unit_of_work: UnitOfWorkDependency, redis_client: RedisClientDependency
) -> AuthService:
    """Фабрика зависимостей для создания экземпляра сервиса аутентификации и авторизации.

    Создает и возвращает функцию-зависимость, которая инстанцирует
    экземпляр сервиса аутентификации и авторизации, используя
    зависимость Unit of Work и RedisClient.

    Parameters
    ----------
    unit_of_work : UnitOfWorkDependency
        Зависимость Unit of Work, которая будет передана
        в конструктор сервиса аутентификации и авторизации.
    redis_client : RedisClientDependency
        Зависимость RedisClient, которая будет передана
        в конструктор сервиса аутентификации и авторизации.

    Returns
    -------
    AuthService
        Экземпляр сервиса аутентификации и авторизации с внедренными
        Unit of Work и RedisClient.
    """
    return AuthService(unit_of_work, redis_client)


AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]
"""Зависимость на получение сервиса аутентификации и авторизации"""
