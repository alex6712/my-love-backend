from abc import ABC

from sqlalchemy.ext.asyncio import AsyncSession


class RepositoryInterface(ABC):
    """Интерфейс репозитория.

    Реализация паттерна Репозиторий. Является интерфейсом доступа к данным (DAO).

    Attributes
    ----------
    session : AsyncSession
        Объект асинхронной сессии запроса.
    """

    def __init__(self, session: AsyncSession):
        self.session: AsyncSession = session
