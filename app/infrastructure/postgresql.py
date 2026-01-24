from typing import Any, Self, TypeVar, cast

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings
from app.core.exceptions.base import UnitOfWorkContextClosedException
from app.repositories.interface import RepositoryInterface

T = TypeVar("T", bound=RepositoryInterface)

settings = get_settings()

async_postgresql_engine = create_async_engine(
    url=settings.POSTGRES_DSN.unicode_string(),
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=10,
)
"""SQLAlchemy async engine, который используется в этом проекте."""

AsyncSessionMaker = async_sessionmaker(
    bind=async_postgresql_engine, class_=AsyncSession, expire_on_commit=False
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
            raise UnitOfWorkContextClosedException()

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
                await self.rollback()
            else:
                await self.commit()
        finally:
            await self.session.close()

            self._session = None
            self._repos.clear()

    async def commit(self) -> None:
        """Зафиксировать изменения в базе данных.

        Применяет все изменения, сделанные в рамках текущей транзакции,
        к базе данных. После успешного вызова все операции insert, update
        и delete становятся постоянными.

        Raises
        ------
        UnitOfWorkContextClosedException
            Если вызван вне контекста менеджера (когда сессия не инициализирована).
        SQLAlchemyError
            При возникновении ошибок на уровне базы данных во время фиксации.

        Notes
        -----
        Обычно этот метод вызывается автоматически при выходе из контекстного
        менеджера, если не возникло исключений. Явный вызов может потребоваться
        для промежуточных фиксаций в рамках одной транзакции.
        """
        await self.session.commit()

    async def rollback(self) -> None:
        """Отменить все изменения в текущей транзакции.

        Откатывает все незафиксированные изменения, сделанные в рамках
        текущей транзакции. После вызова база данных возвращается в состояние,
        которое было до начала транзакции или последнего commit.

        Raises
        ------
        UnitOfWorkContextClosedException
            Если вызван вне контекста менеджера (когда сессия не инициализирована).
        SQLAlchemyError
            При возникновении ошибок на уровне базы данных во время отката.

        Notes
        -----
        Этот метод вызывается автоматически при выходе из контекстного менеджера,
        если в блоке `async with` возникло исключение. Явный вызов может быть
        полезен для отката промежуточных изменений без выхода из контекста.
        """
        await self.session.rollback()

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
