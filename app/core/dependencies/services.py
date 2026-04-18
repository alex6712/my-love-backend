from typing import TYPE_CHECKING, Annotated

from fastapi import Depends

from app.config import Settings
from app.core.dependencies.infra import (
    RedisClientDependency,
    S3ClientDependency,
    UnitOfWorkDependency,
)
from app.core.dependencies.settings import SettingsDependency
from app.infra.postgres.uow import UnitOfWork
from app.infra.redis import RedisClient
from app.services.auth import AuthService
from app.services.couple import CoupleService
from app.services.media import AlbumService, FileService
from app.services.note import NoteService
from app.services.user import UserService

if TYPE_CHECKING:
    from types_aiobotocore_s3 import S3Client


class ServiceManager:
    """Контейнер сервисов уровня запроса (request-scoped).

    Представляет собой менеджер сервисов, который инстанцируется
    один раз на каждый HTTP-запрос и обеспечивает:

    - Единый экземпляр Unit of Work в рамках запроса;
    - Единый доступ к инфраструктурным зависимостям (Redis, S3, Settings);
    - Ленивую (lazy) инициализацию сервисов;
    - Гарантию отсутствия повторных инстансов одного и того же сервиса
      в пределах одного запроса.

    Notes
    -----
    Сервисы создаются только при первом обращении к соответствующему
    свойству и кэшируются внутри менеджера.

    **Важно**: ServiceManager является request-scoped и использует
    один экземпляр UnitOfWork (и, соответственно, одну AsyncSession)
    на весь HTTP-запрос.

    AsyncSession SQLAlchemy не поддерживает конкурентное (coroutine-safe)
    использование. В пределах одного запроса запрещено:
    - вызывать сервисы параллельно через asyncio.gather(...);
    - использовать asyncio.create_task(...) с методами сервисов;
    - передавать сервисы или UnitOfWork в фоновые задачи;
    - выполнять конкурентные операции, использующие одну и ту же сессию.

    Все обращения к сервисам должны выполняться строго последовательно
    через await.

    При необходимости параллелизма каждая конкурентная задача должна
    создавать собственный UnitOfWork (и собственную сессию).
    """

    def __init__(
        self,
        unit_of_work: UnitOfWork,
        redis_client: RedisClient,
        s3_client: "S3Client",
        settings: Settings,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._redis_client = redis_client
        self._s3_client = s3_client
        self._settings = settings

        self._album_service: AlbumService | None = None
        self._file_service: FileService | None = None
        self._auth_service: AuthService | None = None
        self._couple_service: CoupleService | None = None
        self._note_service: NoteService | None = None
        self._user_service: UserService | None = None

    @property
    def album(self) -> AlbumService:
        """Сервис работы с альбомами.

        Returns
        -------
        AlbumService
            Экземпляр сервиса работы с альбомами.
        """
        if self._album_service is None:
            self._album_service = AlbumService(self._unit_of_work)

        return self._album_service

    @property
    def file(self) -> FileService:
        """Сервис работы с файлами.

        Returns
        -------
        FileService
            Экземпляр сервиса работы с файлами.
        """
        if self._file_service is None:
            self._file_service = FileService(
                self._unit_of_work,
                self._redis_client,
                self._s3_client,
                self._settings,
            )

        return self._file_service

    @property
    def auth(self) -> AuthService:
        """Сервис аутентификации и авторизации.

        Returns
        -------
        AuthService
            Экземпляр сервиса аутентификации и авторизации.
        """
        if self._auth_service is None:
            self._auth_service = AuthService(
                self._unit_of_work,
                self._redis_client,
                self._settings,
            )

        return self._auth_service

    @property
    def user(self) -> UserService:
        """Сервис работы с пользователями.

        Returns
        -------
        UserService
            Экземпляр сервиса пользователей.
        """
        if self._user_service is None:
            self._user_service = UserService(self._unit_of_work)

        return self._user_service

    @property
    def couple(self) -> CoupleService:
        """Сервис работы с парами пользователей.

        Returns
        -------
        CoupleService
            Экземпляр сервиса пар пользователей.
        """
        if self._couple_service is None:
            self._couple_service = CoupleService(self._unit_of_work)

        return self._couple_service

    @property
    def note(self) -> NoteService:
        """Сервис работы с заметками.

        Returns
        -------
        NoteService
            Экземпляр сервиса заметок.
        """
        if self._note_service is None:
            self._note_service = NoteService(
                self._unit_of_work,
                self._redis_client,
            )

        return self._note_service


def get_service_manager(
    unit_of_work: UnitOfWorkDependency,
    redis_client: RedisClientDependency,
    s3_client: S3ClientDependency,
    settings: SettingsDependency,
) -> ServiceManager:
    """Фабрика зависимости для создания ServiceManager.

    Создает экземпляр менеджера сервисов, который будет
    существовать в рамках одного HTTP-запроса.

    Parameters
    ----------
    unit_of_work : UnitOfWorkDependency
        Зависимость Unit of Work.
    redis_client : RedisClientDependency
        Зависимость RedisClient.
    s3_client : S3ClientDependency
        Зависимость S3Client.
    settings : SettingsDependency
        Зависимость конфигурации приложения.

    Returns
    -------
    ServiceManager
        Менеджер сервисов с внедренными инфраструктурными зависимостями.
    """
    return ServiceManager(unit_of_work, redis_client, s3_client, settings)


ServiceManagerDependency = Annotated[ServiceManager, Depends(get_service_manager)]
"""Зависимость на получение менеджера сервисов (request-scoped)."""
