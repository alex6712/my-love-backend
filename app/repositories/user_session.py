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
        session_id: UUID,
        user_id: UUID,
        refresh_token_hash: str,
        expires_at: datetime,
        last_used_at: datetime | None,
    ) -> bool:
        """Сохраняет новую пользовательскую сессию в БД.

        Parameters
        ----------
        session_id : UUID
            Идентификатор сессии, сгенерированный на стороне сервиса.
        user_id : UUID
            Идентификатор пользователя, которому принадлежит сессия.
        refresh_token_hash : str
            Хэш refresh-токена, привязанного к сессии.
        expires_at : datetime
            Время истечения сессии.
        last_used_at : datetime | None
            Время последнего использования сессии.
            Передаётся `None`, если сессия только что создана.

        Returns
        -------
        bool
            `True` если сессия успешно создана, `False` в противном случае.

        Raises
        ------
        IntegrityError
            Если сессия с переданным `session_id` уже существует.
        """
        created = await self.session.scalar(
            insert(UserSessionModel)
            .values(
                id=session_id,
                user_id=user_id,
                refresh_token_hash=refresh_token_hash,
                expires_at=expires_at,
                last_used_at=last_used_at,
            )
            .returning(UserSessionModel.id)
        )

        return created is not None

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
    ) -> bool:
        """Обновляет данные сессии по хэшу refresh-токена.

        Используется при ротации refresh-токена - заменяет хэш токена,
        обновляет время истечения и последнего использования сессии.

        Parameters
        ----------
        old_refresh_token_hash : str
            Хэш текущего refresh-токена, по которому ищется сессия.
        new_refresh_token_hash : str
            Хэш нового refresh-токена, который заменит старый.
        expires_at : datetime
            Новое время истечения сессии.
        last_used_at : datetime
            Время последнего использования сессии.

        Returns
        -------
        bool
            `True` если сессия найдена и обновлена, `False` если сессия
            с переданным хэшем не существует или уже неактивна.
        """
        updated = await self.session.scalar(
            update(UserSessionModel)
            .where(UserSessionModel.refresh_token_hash == old_refresh_token_hash)
            .values(
                refresh_token_hash=new_refresh_token_hash,
                expires_at=expires_at,
                last_used_at=last_used_at,
            )
            .returning(UserSessionModel.id)
        )

        return updated is not None

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
