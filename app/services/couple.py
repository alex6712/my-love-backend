from uuid import UUID

from app.core.enums import CoupleRequestStatus
from app.core.exceptions.couple import (
    CoupleAlreadyExistsException,
    CoupleNotSelfException,
    CoupleRequestAlreadyExistsException,
    CoupleRequestNotFoundException,
)
from app.core.exceptions.user import UserNotFoundException
from app.infrastructure.postgresql import UnitOfWork
from app.repositories.couple_request import CoupleRequestRepository
from app.repositories.user import UserRepository
from app.schemas.dto.couple import CoupleRequestDTO
from app.schemas.dto.user import PartnerDTO


class CoupleService:
    """Сервис работы с парами пользователей.

    Реализует бизнес-логику для регистрации и менеджмента
    пар между пользователями.

    Attributes
    ----------
    _user_repo : UserRepository
        Репозиторий для операций с пользователями в БД.
    _couple_request_repo : CoupleRequestRepository
        Репозиторий для операций с парами пользователей в БД.

    Methods
    -------
    get_partner(user_id)
        Получение информации о партнёре пользователя.
    create_couple_request(user_id, partner_username)
        Регистрация пары между пользователями.
    """

    def __init__(self, unit_of_work: UnitOfWork):
        self._user_repo = unit_of_work.get_repository(UserRepository)
        self._couple_request_repo = unit_of_work.get_repository(CoupleRequestRepository)

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
        return await self._couple_request_repo.get_partner_by_user_id(user_id)

    async def create_couple_request(
        self, initiator_id: UUID, recipient_username: str
    ) -> None:
        """Создание приглашения к регистрации новой пары.

        Выполняет несколько проверок, а именно:
        - оба переданных UUID должны быть уникальными;
        - существуют ли пользователи с переданными UUID;
        - состоят ли пользователи в паре или в других парах;
        - уже отправлено подобное приглашение.

        Если все проверки пройдены успешно, создаёт приглашение.

        Parameters
        ----------
        initiator_id : UUID
            UUID пользователя-инициатора.
        recipient_username : str
            Username пользователя-реципиента.

        Raises
        ------
        UserNotFoundException
            Если пользователь с переданным username не найден.
        CoupleNotSelfException
            Если переданы два совпадающих UUID.
        CoupleAlreadyExistsException
            Если по переданным UUID найдена пара.
        CoupleRequestAlreadyExistsException
            Если уже отправлено подобное приглашение.
        """
        recipient_user = await self._user_repo.get_user_by_username(recipient_username)
        if recipient_user is None:
            raise UserNotFoundException(
                detail=f"User with username={recipient_username} not found."
            )
        recipient_id = recipient_user.id

        if initiator_id == recipient_id:
            raise CoupleNotSelfException(detail="Cannot register couple with yourself!")

        if not await self._user_repo.user_exists_by_id(initiator_id):
            raise UserNotFoundException(
                detail=f"User with id={initiator_id} not found."
            )

        # TODO: заменить на ОДИН запрос
        if await self._couple_request_repo.get_active_couple_by_partner_id(
            initiator_id
        ):
            raise CoupleAlreadyExistsException(detail="You're already in couple!")
        if await self._couple_request_repo.get_active_couple_by_partner_id(
            recipient_id
        ):
            raise CoupleAlreadyExistsException(
                detail=f"User with username={recipient_username} is already in couple!",
            )

        if await self._couple_request_repo.find_existing_request(
            initiator_id, recipient_id
        ):
            raise CoupleRequestAlreadyExistsException(
                detail=f"Couple request with UUIDs {initiator_id} <-> {recipient_id} already exists!"
            )

        self._couple_request_repo.add_couple_request(initiator_id, recipient_id)

    async def accept_couple_request(self, couple_id: UUID, user_id: UUID) -> None:
        """Подтверждение запроса на создание пары между пользователями.

        Проверяет, существует ли для текущего пользователя с UUID=`user_id`
        запрос на создание пары с UUID=`couple_id`. Далее проверяет, не состоит
        ли уже текущий пользователь в паре.

        Если всё хорошо, подтверждает создание пары.

        Parameters
        ----------
        couple_id : UUID
            UUID запроса на создание пары.
        user_id : UUID
            UUID пользователя.

        Raises
        ------
        CoupleRequestNotFoundException
            Если запрос с переданным UUID не найден в запросах к текущему пользователю.
        """
        request = (
            await self._couple_request_repo.get_pending_request_by_id_and_recipient_id(
                couple_id, user_id
            )
        )

        if request is None:
            raise CoupleRequestNotFoundException(
                detail=f"Couple request with id={couple_id} not found in pending requests for user with id={user_id}.",
            )

        active_couples = (
            await self._couple_request_repo.get_active_couples_by_partner_ids(
                user_id, request.initiator.id
            )
        )

        if active_couples:
            active_couple = active_couples[0]

            if user_id in (active_couple.initiator.id, active_couple.recipient.id):
                raise CoupleAlreadyExistsException(detail="You're already in couple!")

            raise CoupleAlreadyExistsException(
                detail=f"User with id={request.initiator.id} is already in couple!",
            )

        updated = await self._couple_request_repo.update_request_status_by_id_and_recipient_id(
            couple_id, user_id, CoupleRequestStatus.ACCEPTED
        )

        if not updated:
            raise CoupleRequestNotFoundException(
                detail=f"Failed to accept pending couple request with id={couple_id}.",
            )

    async def decline_couple_request(self, couple_id: UUID, user_id: UUID) -> None:
        """Отклонение запроса на создание пары между пользователями.

        Инициирует попытку атомарно отклонить запрос на создание пары.
        Если запрос по переданным параметрам найден, то ему устанавливается
        статус `CoupleRequestStatus.DECLINED`.

        Parameters
        ----------
        couple_id : UUID
            UUID запроса на создание пары.
        user_id : UUID
            UUID пользователя.

        Raises
        ------
        CoupleRequestNotFoundException
            Если запрос с переданным UUID не найден в запросах к текущему пользователю.
        """
        updated = await self._couple_request_repo.update_request_status_by_id_and_recipient_id(
            couple_id, user_id, CoupleRequestStatus.DECLINED
        )

        if not updated:
            raise CoupleRequestNotFoundException(
                detail=f"Couple request with id={couple_id} not found.",
            )

    async def get_couple_requests(self, user_id: UUID) -> list[CoupleRequestDTO]:
        """Получение списка всех запросов на создание пары.

        Получает на вход UUID пользователя, для которого проводится поиск запросов
        со статусом `CoupleRequestStatus.PENDING`.

        Parameters
        ----------
        user_id : UUID
            UUID пользователя для поиска.

        Returns
        -------
        list[CoupleRequestDTO]
            Список всех текущих запросов на создание пары.
        """
        return await self._couple_request_repo.get_pending_requests_for_recipient(
            user_id
        )
