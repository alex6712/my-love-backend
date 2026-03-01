from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_session import UserSessionModel
from app.repositories.interface import RepositoryInterface
from app.schemas.dto.user_session import UserSessionDTO


class UserSessionRepository(RepositoryInterface):
    """Репозиторий для управления пользовательскими сессиями.

    Реализует CRUD-операции над таблицей пользовательских сессий
    через SQLAlchemy AsyncSession.

    Methods
    -------
    add_user_session(user_id, refresh_token_hash, expires_at, last_used_at)
        Создаёт новую пользовательскую сессию.
    get_user_session_by_id(session_id)
        Возвращает сессию по её идентификатору.
    get_user_session_by_refresh_token_hash(refresh_token_hash)
        Возвращает сессию по хешу refresh-токена.
    update_user_session_by_refresh_token_hash(old_refresh_token_hash, ne_refresh_token_hash, expires_at, last_used_at)
        Обновляет данные сессии по хэшу токена обновления.
    delete_user_session_by_id(session_id)
        Удаляет сессию по её идентификатору.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def add_user_session(
        self,
        user_id: UUID,
        refresh_token_hash: str,
        expires_at: datetime,
        last_used_at: datetime | None,
    ) -> UUID:
        """Создаёт новую пользовательскую сессию.

        Parameters
        ----------
        user_id : UUID
            Идентификатор пользователя, которому принадлежит сессия.
        refresh_token_hash : str
            Хэш refresh-токена, привязанного к сессии.
        expires_at : datetime
            Время истечения сессии.
        last_used_at : datetime | None
            Время последнего использования сессии.
            Может быть ``None``, если сессия только что создана.

        Returns
        -------
        UUID
            Идентификатор созданной сессии.

        Raises
        ------
        RuntimeError
            Если БД не вернула идентификатор после вставки.
        """
        session_id = await self.session.scalar(
            insert(UserSessionModel)
            .values(
                user_id=user_id,
                refresh_token_hash=refresh_token_hash,
                expires_at=expires_at,
                last_used_at=last_used_at,
            )
            .returning(UserSessionModel.id)
        )

        if not session_id:
            raise RuntimeError(
                "Unknown error is occurred while trying to create new user session."
            )

        return session_id

    async def get_user_session_by_id(self, session_id: UUID) -> UserSessionDTO | None:
        """Возвращает сессию по её идентификатору.

        Parameters
        ----------
        session_id : UUID
            Идентификатор сессии.

        Returns
        -------
        UserSessionDTO | None
            DTO сессии или `None`, если сессия не найдена.
        """
        user_session = await self.session.scalar(
            select(UserSessionModel).where(UserSessionModel.id == session_id)
        )

        return UserSessionDTO.model_validate(user_session) if user_session else None

    async def get_user_session_by_refresh_token_hash(
        self, refresh_token_hash: str
    ) -> UserSessionDTO | None:
        """Возвращает сессию по хешу refresh-токена.

        Parameters
        ----------
        refresh_token_hash : str
            Хэш refresh-токена.

        Returns
        -------
        UserSessionDTO | None
            DTO сессии или `None`, если сессия не найдена.
        """
        user_session = await self.session.scalar(
            select(UserSessionModel).where(
                UserSessionModel.refresh_token_hash == refresh_token_hash
            )
        )

        return UserSessionDTO.model_validate(user_session) if user_session else None

    async def update_user_session_by_refresh_token_hash(
        self,
        old_refresh_token_hash: str,
        new_refresh_token_hash: str,
        expires_at: datetime,
        last_used_at: datetime,
    ) -> UUID | None:
        """Обновляет данные сессии по хэшу токена обновления.

        Используется, например, при ротации refresh-токена -
        когда нужно заменить хэш и обновить время истечения и последнего использования.

        Parameters
        ----------
        old_refresh_token_hash : str
            Старый хэш refresh-токена.
        new_refresh_token_hash : str
            Новый хэш refresh-токена.
        expires_at : datetime
            Новое время истечения сессии.
        last_used_at : datetime
            Время последнего использования сессии.

        Returns
        -------
        UUID | None
            Уникальный идентификатор сессии пользователя.
        """
        user_session_id = await self.session.scalar(
            update(UserSessionModel)
            .where(UserSessionModel.refresh_token_hash == old_refresh_token_hash)
            .values(
                refresh_token_hash=new_refresh_token_hash,
                expires_at=expires_at,
                last_used_at=last_used_at,
            )
            .returning(UserSessionModel.id)
        )

        return user_session_id

    async def delete_user_session_by_id(self, session_id: UUID) -> None:
        """Удаляет сессию по её идентификатору.

        Parameters
        ----------
        session_id : UUID
            Идентификатор удаляемой сессии.
        """
        await self.session.execute(
            delete(UserSessionModel).where(UserSessionModel.id == session_id)
        )
