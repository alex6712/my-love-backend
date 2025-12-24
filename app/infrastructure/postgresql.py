from typing import Any, Self, TypeVar, cast

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings, get_settings
from app.core.exceptions.base import UnitOfWorkContextClosedException
from app.repositories.interface import RepositoryInterface

T = TypeVar("T", bound=RepositoryInterface)

settings: Settings = get_settings()

engine: AsyncEngine = create_async_engine(
    url=settings.POSTGRES_DSN,
    echo=False,
    pool_pre_ping=True,
)
"""SQLAlchemy async engine, который используется в этом проекте."""

AsyncSessionMaker: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)
"""Фабрика асинхронных сессий SQLAlchemy."""


class UnitOfWork:
    """Единица работы (Unit of Work) для управления транзакцией и репозиториями.

    Класс инкапсулирует работу с асинхронной сессией SQLAlchemy, обеспечивает
    атомарность операций (commit/rollback) и управление жизненным циклом репозиториев.

    Parameters
    ----------
    session_maker : async_sessionmaker[AsyncSession]
        Фабрика асинхронных сессий SQLAlchemy. По умолчанию используется
        глобальный `AsyncSessionMaker`.

    Attributes
    ----------
    session : AsyncSession
        Текущая асинхронная сессия. Доступна только в пределах контекста
        (`async with UnitOfWork(): ...`).
    _repos : dict[type[RepositoryInterface], RepositoryInterface]
        Кэш созданных репозиториев для повторного использования в пределах
        одной транзакции.

    Raises
    ------
    UnitOfWorkContextClosedException
        Если попытаться получить доступ к сессии вне контекстного менеджера.
    """

    def __init__(
        self, session_maker: async_sessionmaker[AsyncSession] = AsyncSessionMaker
    ):
        self.session_maker = session_maker
        self._session: AsyncSession | None = None

        self._repos: dict[type[RepositoryInterface], RepositoryInterface] = {}

    @property
    def session(self) -> AsyncSession:
        if self._session is None:
            raise UnitOfWorkContextClosedException(domain="application")

        return self._session

    async def __aenter__(self) -> Self:
        """Вход в асинхронный контекст.

        Создаёт новую асинхронную сессию и возвращает объект `UnitOfWork`.

        Returns
        -------
        UnitOfWork
            Текущий экземпляр `UnitOfWork`.
        """
        self._session = self.session_maker()
        return self

    async def __aexit__(self, exc_type: Any, *_: Any) -> None:
        """Выход из асинхронного контекста.

        В случае возникновения ошибки выполняется `rollback`, иначе — `commit`.
        После завершения сессия закрывается, а все кэшированные репозитории очищаются.

        Parameters
        ----------
        exc_type : Any
            Тип исключения, если оно возникло.
        """
        try:
            if exc_type is not None:
                await self.session.rollback()
            else:
                await self.session.commit()
        finally:
            await self.session.close()

            self._session = None
            self._repos.clear()

    def get_repository(self, repo_type: type[T]) -> T:
        """Получить экземпляр репозитория для работы с базой данных.

        Если репозиторий указанного типа ещё не был создан, он будет
        инициализирован с текущей сессией и сохранён в кэше.

        Parameters
        ----------
        repo_type : type[T]
            Класс репозитория, реализующий интерфейс `RepositoryInterface`.

        Returns
        -------
        T
            Экземпляр репозитория, связанный с текущей сессией.
        """
        if repo_type not in self._repos:
            self._repos[repo_type] = repo_type(self.session)

        return cast(T, self._repos[repo_type])
