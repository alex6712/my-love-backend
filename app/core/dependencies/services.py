from typing import Annotated

from fastapi import Depends

from app.core.dependencies.infrastructure import (
    MinioClientDependency,
    RedisClientDependency,
    UnitOfWorkDependency,
)
from app.core.dependencies.settings import SettingsDependency
from app.services.auth import AuthService
from app.services.couples import CouplesService
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
    minio_client: MinioClientDependency,
    settings: SettingsDependency,
) -> MediaService:
    """Фабрика зависимостей для создания экземпляра сервиса работы с медиа.

    Создает и возвращает функцию-зависимость, которая инстанцирует
    экземпляр сервиса работы с медиа, используя
    зависимости Unit of Work, MinIO Client и Settings.

    Parameters
    ----------
    unit_of_work : UnitOfWorkDependency
        Зависимость Unit of Work, которая будет передана
        в конструктор сервиса работы с медиа.
    minio_client: MinioClientDependency
        Зависимость MinioClient для работы с файловым хранилищем.
    settings : SettingsDependency
        Зависимость для установки точного пути до сохранённых медиа.

    Returns
    -------
    MediaService
        Экземпляр сервиса работы с медиа с внедренными зависимостями.
    """
    return MediaService(unit_of_work, minio_client, settings)


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
        Экземпляр сервиса пользователей с внедренным Unit of Work.
    """
    return UsersService(unit_of_work)


def get_couples_service(
    unit_of_work: UnitOfWorkDependency,
) -> CouplesService:
    """Фабрика зависимостей для создания экземпляра сервиса пар пользователей.

    Создает и возвращает функцию-зависимость, которая инстанцирует
    экземпляр сервиса пар пользователей, используя
    зависимость Unit of Work.

    Parameters
    ----------
    unit_of_work : UnitOfWorkDependency
        Зависимость Unit of Work, которая будет передана
        в конструктор сервиса пар пользователей.

    Returns
    -------
    CouplesService
        Экземпляр сервиса пар пользователей с внедренным Unit of Work.
    """
    return CouplesService(unit_of_work)


AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]
"""Зависимость на получение сервиса аутентификации и авторизации."""

MediaServiceDependency = Annotated[MediaService, Depends(get_media_service)]
"""Зависимость на получение сервиса работы с медиа."""

UsersServiceDependency = Annotated[UsersService, Depends(get_users_service)]
"""Зависимость на получение сервиса пользователей."""

CouplesServiceDependency = Annotated[CouplesService, Depends(get_couples_service)]
"""Зависимость на получение сервиса пар пользователей."""
