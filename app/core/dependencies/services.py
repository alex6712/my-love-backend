from typing import Annotated

from fastapi import Depends

from app.core.dependencies.infrastructure import (
    RedisClientDependency,
    UnitOfWorkDependency,
)
from app.services.auth import AuthService
from app.services.media import MediaService
from app.services.users import UsersService


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


def get_media_service(
    unit_of_work: UnitOfWorkDependency,
) -> MediaService:
    """Фабрика зависимостей для создания экземпляра сервиса работы с медиа.

    Создает и возвращает функцию-зависимость, которая инстанцирует
    экземпляр сервиса работы с медиа, используя
    зависимость Unit of Work.

    Parameters
    ----------
    unit_of_work : UnitOfWorkDependency
        Зависимость Unit of Work, которая будет передана
        в конструктор сервиса работы с медиа.

    Returns
    -------
    MediaService
        Экземпляр сервиса работы с медиа с внедренными
        Unit of Work.
    """
    return MediaService(unit_of_work)


def get_users_service(
    unit_of_work: UnitOfWorkDependency,
) -> UsersService:
    """Фабрика зависимостей для создания экземпляра сервиса пользователей.

    Создает и возвращает функцию-зависимость, которая инстанцирует
    экземпляр сервиса пользователей, используя
    зависимость Unit of Work.

    Parameters
    ----------
    unit_of_work : UnitOfWorkDependency
        Зависимость Unit of Work, которая будет передана
        в конструктор сервиса пользователей.

    Returns
    -------
    UsersService
        Экземпляр сервиса пользователей с внедренными
        Unit of Work.
    """
    return UsersService(unit_of_work)


AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]
"""Зависимость на получение сервиса аутентификации и авторизации."""

MediaServiceDependency = Annotated[MediaService, Depends(get_media_service)]
"""Зависимость на получение сервиса работы с медиа."""

UsersServiceDependency = Annotated[UsersService, Depends(get_users_service)]
"""Зависимость на получение сервиса пользователей."""
