from typing import Annotated

from fastapi import Depends

from app.core.dependencies.infrastructure import (
    RedisClientDependency,
    S3ClientDependency,
    UnitOfWorkDependency,
)
from app.core.dependencies.settings import SettingsDependency
from app.services.auth import AuthService
from app.services.couple import CoupleService
from app.services.media import AlbumService, FileService
from app.services.note import NoteService
from app.services.user import UserService


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


def get_auth_service(
    unit_of_work: UnitOfWorkDependency,
    redis_client: RedisClientDependency,
    settings: SettingsDependency,
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
    settings : SettingsDependency
        Зависимость настроек приложения.

    Returns
    -------
    AuthService
        Экземпляр сервиса аутентификации и авторизации с внедренными
        Unit of Work и RedisClient.
    """
    return AuthService(unit_of_work, redis_client, settings)


def get_couple_service(
    unit_of_work: UnitOfWorkDependency,
) -> CoupleService:
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
    CoupleService
        Экземпляр сервиса пар пользователей с внедренным Unit of Work.
    """
    return CoupleService(unit_of_work)


def get_note_service(
    unit_of_work: UnitOfWorkDependency,
) -> NoteService:
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
    NoteService
        Экземпляр сервиса заметок с внедренным Unit of Work.
    """
    return NoteService(unit_of_work)


def get_user_service(
    unit_of_work: UnitOfWorkDependency,
) -> UserService:
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
    UserService
        Экземпляр сервиса пользователей с внедренным Unit of Work.
    """
    return UserService(unit_of_work)


AlbumServiceDependency = Annotated[AlbumService, Depends(get_album_service)]
"""Зависимость на получение сервиса работы с альбомами."""

FileServiceDependency = Annotated[FileService, Depends(get_file_service)]
"""Зависимость на получение сервиса работы с файлами."""

AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]
"""Зависимость на получение сервиса аутентификации и авторизации."""

CoupleServiceDependency = Annotated[CoupleService, Depends(get_couple_service)]
"""Зависимость на получение сервиса пар пользователей."""

NoteServiceDependency = Annotated[NoteService, Depends(get_note_service)]
"""Зависимость на получение сервиса заметок."""

UserServiceDependency = Annotated[UserService, Depends(get_user_service)]
"""Зависимость на получение сервиса пользователей."""
