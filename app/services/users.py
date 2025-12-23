from uuid import UUID

from app.core.exceptions import (
    CoupleAlreadyExistsException,
    CoupleNotSelfException,
)
from app.infrastructure.postgresql import UnitOfWork
from app.repositories.user import UserRepository
from app.schemas.dto.user import PartnerDTO


class UsersService:
    """Сервис работы с пользователями.

    Реализует бизнес-логику для регистрации и менеджмента
    пар между пользователями.

    Attributes
    ----------
    _user_repo : UserRepository
        Репозиторий для операций с пользователями в БД.

    Methods
    -------
    get_partner(user_id)
        Получение информации о партнёре пользователя.
    register_couple(user_id, partner_id)
        Регистрация пары между пользователями.
    """

    def __init__(self, unit_of_work: UnitOfWork):
        super().__init__()

        self._user_repo: UserRepository = unit_of_work.get_repository(UserRepository)

    async def get_partner(self, user_id: UUID) -> PartnerDTO | None:
        """Получение информации о партнёре пользователя.

        Возвращает DTO пользователя-партнёра по UUID текущего
        пользователя.

        Parameters
        ----------
        user_id : UUID
            UUID пользователя.

        Returns
        -------
        PartnerDTO | None
            Информация о партнёре пользователя.
        """
        return await self._user_repo.get_partner_by_user_id(user_id)

    async def register_couple(self, user_id: UUID, partner_id: UUID) -> None:
        """Регистрация пары между пользователями.

        Выполняет несколько проверок, а именно:
        - оба переданных UUID должны быть уникальными;
        - существуют ли пользователи с переданными UUID;
        - состоят ли пользователи в паре или в других парах.

        Если все проверки пройдены успешно, регистрирует новую пару пользователей.

        Parameters
        ----------
        partner1_id : UUID
            UUID первого пользователя пары.
        partner2_id : UUID
            UUID второго пользователя пары.

        Raises
        ------
        CoupleAlreadyExistsException
            Если по переданным UUID найдена пара.
        """
        # проверка на уникальность UUID
        if user_id == partner_id:
            raise CoupleNotSelfException(detail="Cannot register couple with yourself!")

        # проверка на существование пользователей
        _ = await self._user_repo.get_user_by_id(user_id)
        _ = await self._user_repo.get_user_by_id(partner_id)

        # проверка, состоят ли пользователи в паре (не только между собой)
        if await self._user_repo.get_couple_by_partner_id(user_id):
            raise CoupleAlreadyExistsException(detail="You're already in couple!")

        if await self._user_repo.get_couple_by_partner_id(partner_id):
            raise CoupleAlreadyExistsException(
                detail=f"User with id={partner_id} is already in couple!",
            )

        # если всё хорошо, и исключения не были выброшены, регистрируем пару
        await self._user_repo.register_couple(user_id, partner_id)
