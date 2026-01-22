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
from app.services.media import AlbumsService, FilesService
from app.services.notes import NotesService
from app.services.users import UsersService


def get_albums_service(
    unit_of_work: UnitOfWorkDependency,
) -> AlbumsService:
    """Фабрика зависимостей для создания экземпляра сервиса работы с альбомами.

    Создает и возвращает функцию-зависимость, которая инстанцирует
    экземпляр сервиса работы с альбомами.

    Parameters
    ----------
    unit_of_work : UnitOfWorkDependency
        Зависимость Unit of Work.

    Returns
    -------
    AlbumsService
        Экземпляр сервиса работы с альбомами.
    """
    return AlbumsService(unit_of_work)


def get_files_service(
    unit_of_work: UnitOfWorkDependency,
    redis_client: RedisClientDependency,
    s3_client: S3ClientDependency,
    settings: SettingsDependency,
) -> FilesService:
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
    FilesService
        Экземпляр сервиса работы с файлами.
    """
    return FilesService(unit_of_work, redis_client, s3_client, settings)


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


def get_notes_service(
    unit_of_work: UnitOfWorkDependency,
) -> NotesService:
    """Фабрика зависимостей для создания экземпляра сервиса заметок.

    Создает и возвращает функцию-зависимость, которая инстанцирует
    экземпляр сервиса заметок, используя
    зависимость Unit of Work.

    Parameters
    ----------
    unit_of_work : UnitOfWorkDependency
        Зависимость Unit of Work, которая будет передана
        в конструктор сервиса заметок.

    Returns
    -------
    NotesService
        Экземпляр сервиса заметок с внедренным Unit of Work.
    """
    return NotesService(unit_of_work)


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


AlbumsServiceDependency = Annotated[AlbumsService, Depends(get_albums_service)]
"""Зависимость на получение сервиса работы с альбомами."""

FilesServiceDependency = Annotated[FilesService, Depends(get_files_service)]
"""Зависимость на получение сервиса работы с файлами."""

AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]
"""Зависимость на получение сервиса аутентификации и авторизации."""

CouplesServiceDependency = Annotated[CouplesService, Depends(get_couples_service)]
"""Зависимость на получение сервиса пар пользователей."""

NotesServiceDependency = Annotated[NotesService, Depends(get_notes_service)]
"""Зависимость на получение сервиса заметок."""

UsersServiceDependency = Annotated[UsersService, Depends(get_users_service)]
"""Зависимость на получение сервиса пользователей."""
