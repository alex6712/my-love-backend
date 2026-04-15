from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.couple import CoupleModel
from app.repositories.interface import RepositoryInterface


class CoupleRepository(RepositoryInterface):
    """Репозиторий пар между пользователями.

    Реализация паттерна Репозиторий. Является объектом доступа к данным (DAO).
    Реализует основные CRUD операции с парами пользователей.

    Attributes
    ----------
    session : AsyncSession
        Объект асинхронной сессии запроса.

    Methods
    -------
    add_couple(initiator_id, recipient_id)
        Регистрация пары между пользователями.
    get_partner_by_user_id(user_id)
        Получение информации о партнёре пользователя.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    def add_couple(self, user_low_id: UUID, user_high_id: UUID) -> None:
        """Создание записи о зарегистрированной паре между пользователями.

        Добавляет в базу данных запись о новой паре между пользователями,
        изначально эта пара имеет статус `Couple.Status.PENDING`, пока реципиент не подтвердит
        приглашение инициатора.

        Parameters
        ----------
        user_low_id : UUID
            UUID пользователя-инициатора.
        user_high_id : UUID
            UUID пользователя-реципиента.
        """
        self.session.add(
            CoupleModel(user_low_id=user_low_id, user_high_id=user_high_id)
        )

    async def get_partner_id_by_user_id(self, user_id: UUID) -> UUID | None:
        """Получение UUID партнёра пользователя.

        Получает UUID пользователя, после чего ищет в БД запись
        о паре пользователей и возвращает UUID партнёра пользователя.

        Parameters
        ----------
        user_id : UUID
            UUID пользователя в системе.

        Returns
        -------
        UUID | None
            UUID партнёра пользователя или None, если пользователь не в паре.
        """
        couple = await self.session.scalar(
            select(CoupleModel).where(
                or_(
                    CoupleModel.user_low_id == user_id,
                    CoupleModel.user_high_id == user_id,
                ),
            )
        )

        if couple is None:
            return None

        return (
            couple.user_low_id
            if couple.user_high_id == user_id
            else couple.user_high_id
        )
