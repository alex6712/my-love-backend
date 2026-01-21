from typing import Annotated

from fastapi import Depends

from app.core.dependencies.infrastructure import (
    RedisClientDependency,
    S3ClientDependency,
    UnitOfWorkDependency,
)
from app.core.dependencies.settings import SettingsDependency
from app.services.auth import AuthService
from app.services.couples import CouplesService
from app.services.media import AlbumService, FileService
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


def get_file_service(
    unit_of_work: UnitOfWorkDependency,
    redis_client: RedisClientDependency,
    s3_client: S3ClientDependency,
    settings: SettingsDependency,
) -> FileService:
    """Фабрика зависимостей для создания экземпляра сервиса работы с файлами.

    Создает и возвращает функцию-зависимость, которая инстанцирует
    экземпляр сервиса работы с файлами.

    Parameters
    ----------
    unit_of_work : UnitOfWorkDependency
        Зависимость Unit of Work.
    redis_client : RedisClientDependency
        Зависимость RedisClient.
    s3_client : S3ClientDependency
        Зависимость S3Client для работы с файловым хранилищем.
    settings : SettingsDependency
        Зависимость настроек приложения.

    Returns
    -------
    FileService
        Экземпляр сервиса работы с файлами.
    """
    return FileService(unit_of_work, redis_client, s3_client, settings)


def get_album_service(
    unit_of_work: UnitOfWorkDependency,
) -> AlbumService:
    """Фабрика зависимостей для создания экземпляра сервиса работы с альбомами.

    Создает и возвращает функцию-зависимость, которая инстанцирует
    экземпляр сервиса работы с альбомами.

    Parameters
    ----------
    unit_of_work : UnitOfWorkDependency
        Зависимость Unit of Work.

    Returns
    -------
    AlbumService
        Экземпляр сервиса работы с альбомами.
    """
    return AlbumService(unit_of_work)


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

FileServiceDependency = Annotated[FileService, Depends(get_file_service)]
"""Зависимость на получение сервиса работы с файлами."""

AlbumServiceDependency = Annotated[AlbumService, Depends(get_album_service)]
"""Зависимость на получение сервиса работы с альбомами."""

UsersServiceDependency = Annotated[UsersService, Depends(get_users_service)]
"""Зависимость на получение сервиса пользователей."""

CouplesServiceDependency = Annotated[CouplesService, Depends(get_couples_service)]
"""Зависимость на получение сервиса пар пользователей."""
