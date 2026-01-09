from uuid import UUID

from sqlalchemy import select, update  # type: ignore # noqa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.idempotency_key import IdempotencyKeyModel
from app.repositories.interface import RepositoryInterface


class IdempotencyRepository(RepositoryInterface):
    """Репозиторий ключей идемпотентности.

    Реализация паттерна Репозиторий. Является интерфейсом
    взаимодействия системы с базой данных и менеджмента
    ключей идемпотентности.

    Attributes
    ----------
    session : AsyncSession
        Объект асинхронной сессии запроса.

    Methods
    -------
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    def add_key(self, scope: str, entity_id: UUID) -> None:
        self.session.add(
            IdempotencyKeyModel(
                scope=scope,
                entity_id=entity_id,
            )
        )
