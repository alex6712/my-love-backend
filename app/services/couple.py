import asyncio
from datetime import datetime, timezone
from uuid import UUID

from app.core.enums import CoupleRequestStatus
from app.core.exceptions.base import NothingToUpdateException
from app.core.exceptions.couple import (
    CoupleAlreadyExistsException,
    CoupleNotFoundException,
    CoupleRequestNotFoundException,
)
from app.core.exceptions.user import UserNotFoundException
from app.infra.postgres.uow import UnitOfWork
from app.repositories.couple import CoupleRepository
from app.repositories.couple_request import CoupleRequestRepository
from app.repositories.interface import PublicAccessContext
from app.repositories.user import UserRepository
from app.schemas.dto.couple import (
    CoupleRequestDTO,
    CreateCoupleDTO,
    CreateCoupleRequestDTO,
    FilterManyCoupleRequestsDTO,
    FilterOneCoupleDTO,
    FilterOneCoupleRequestDTO,
    UpdateCoupleDTO,
    UpdateCoupleRequestDTO,
)
from app.schemas.dto.user import FilterUserDTO, PartnerDTO


class CoupleService:
    """Сервис работы с парами пользователей.

    Реализует бизнес-логику для регистрации и менеджмента
    пар между пользователями.

    Attributes
    ----------
    _user_repo : UserRepository
        Репозиторий для операций с пользователями в БД.
    _couple_repo : CoupleRepository
        Репозиторий для операций с парами пользователей в БД.
    _couple_request_repo : CoupleRequestRepository
        Репозиторий для операций с запросами на создание пар пользователей в БД.

    Methods
    -------
    get_partner(user_id)
        Получение информации о партнёре пользователя.
    create_couple_request(user_id, partner_username)
        Регистрация пары между пользователями.
    """

    def __init__(self, unit_of_work: UnitOfWork):
        self._user_repo = unit_of_work.get_repository(UserRepository)
        self._couple_repo = unit_of_work.get_repository(CoupleRepository)
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
        couple = await self._couple_repo.read_one(
            FilterOneCoupleDTO(user_id=user_id), PublicAccessContext()
        )
        if couple is None:
            return None

        return (
            couple.first_user
            if couple.second_user.id == user_id
            else couple.second_user
        )

    async def create_couple_request(
        self, initiator_id: UUID, recipient_username: str
    ) -> None:
        """Создание запрос на создание новой пары между пользователями.

        Выполняет несколько проверок, а именно:
        - пользователь-реципиент с переданным username должен существовать;
        - пользователь-реципиент не может быть пользователем-инициатором;
        - состоят ли пользователи в паре или в других парах;
        - уже отправлен подобный запрос.

        Если все проверки пройдены успешно, создаёт запрос.

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
            Если хотя бы один из пользователей уже состоит в паре.
        CoupleRequestAlreadyExistsException
            Если уже отправлен подобный запрос.
        """
        recipient_user = await self._user_repo.get_one_filtered(
            FilterUserDTO(username=recipient_username)
        )
        if recipient_user is None:
            raise UserNotFoundException(
                detail=f"User with username={recipient_username} not found."
            )

        first_couple, second_couple = await asyncio.gather(
            *[
                self._couple_repo.read_one(
                    FilterOneCoupleDTO(user_id=user_id), PublicAccessContext()
                )
                for user_id in (initiator_id, recipient_user.id)
            ],
        )

        if first_couple is not None:
            raise CoupleAlreadyExistsException(detail="You're already in couple!")
        elif second_couple is not None:
            raise CoupleAlreadyExistsException(
                detail=f"User with username={recipient_username} is already in couple!",
            )

        await self._couple_request_repo.create_one(
            CreateCoupleRequestDTO(
                initiator_id=initiator_id,
                recipient_id=recipient_user.id,
                status=CoupleRequestStatus.PENDING,
                accepted_at=None,
            )
        )

    async def accept_couple_request(
        self, couple_request_id: UUID, user_id: UUID
    ) -> None:
        """Подтверждение запроса на создание пары между пользователями.

        Проверяет, существует ли для текущего пользователя с UUID=`user_id`
        запрос на создание пары с UUID=`couple_request_id`. Далее проверяет, не состоит
        ли уже текущий пользователь в паре.

        Если всё хорошо, подтверждает создание пары.

        Parameters
        ----------
        couple_request_id : UUID
            UUID запроса на создание пары.
        user_id : UUID
            UUID пользователя.

        Raises
        ------
        CoupleRequestNotFoundException
            Если запрос с переданным UUID не найден в запросах к текущему пользователю.
        """
        locked = await self._couple_request_repo.read_one_for_update(
            filter_dto := FilterOneCoupleRequestDTO(
                id=couple_request_id,
                recipient_id=user_id,
                statuses=[CoupleRequestStatus.PENDING],
            ),
            PublicAccessContext(),
        )
        if locked is None:
            raise CoupleRequestNotFoundException(
                detail=f"Failed to accept pending couple request with id={couple_request_id}.",
            )

        updated = await self._couple_request_repo.update_one(
            filter_dto,
            UpdateCoupleRequestDTO(
                status=CoupleRequestStatus.ACCEPTED,
                accepted_at=datetime.now(timezone.utc),
            ),
            PublicAccessContext(),
        )
        if not updated:
            raise CoupleRequestNotFoundException(
                detail=f"Failed to accept pending couple request with id={couple_request_id}.",
            )

        await self._couple_repo.create_one(
            CreateCoupleDTO(
                first_user_id=locked.initiator.id,
                second_user_id=locked.recipient.id,
                relationship_started_on=None,
            )
        )

    async def decline_couple_request(
        self, couple_request_id: UUID, user_id: UUID
    ) -> None:
        """Отклонение запроса на создание пары между пользователями.

        Инициирует попытку атомарно отклонить запрос на создание пары.
        Если запрос по переданным параметрам найден, то ему устанавливается
        статус `CoupleRequestStatus.DECLINED`.

        Parameters
        ----------
        couple_request_id : UUID
            UUID запроса на создание пары.
        user_id : UUID
            UUID пользователя.

        Raises
        ------
        CoupleRequestNotFoundException
            Если запрос с переданным UUID не найден в запросах к текущему пользователю.
        """
        updated = await self._couple_request_repo.update_one(
            FilterOneCoupleRequestDTO(
                id=couple_request_id,
                recipient_id=user_id,
                statuses=[CoupleRequestStatus.PENDING],
            ),
            UpdateCoupleRequestDTO(status=CoupleRequestStatus.DECLINED),
            PublicAccessContext(),
        )
        if not updated:
            raise CoupleRequestNotFoundException(
                detail=f"Couple request with id={couple_request_id} not found.",
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
        return (
            await self._couple_request_repo.read_many(
                FilterManyCoupleRequestsDTO(
                    recipient_ids=[user_id],
                    statuses=[CoupleRequestStatus.PENDING],
                ),
                PublicAccessContext(),
            )
        )[0]

    async def update_couple(
        self, couple_id: UUID, update_dto: UpdateCoupleDTO, user_id: UUID
    ) -> None:
        """Частичное обновление атрибутов пары по её UUID.

        Получает идентификатор пары и текущего пользователя и передаёт данные
        в репозиторий для обновления пары с учётом прав доступа.
        Обновляет только явно переданные поля (не равные `UNSET`).

        Parameters
        ----------
        couple_id : UUID
            UUID пары к изменению.
        update_dto : UpdateCoupleDTO
            DTO с полями для обновления. Содержит только явно переданные поля.
        user_id : UUID
            UUID пользователя, инициирующего изменение пары.

        Raises
        ------
        NothingToUpdateException
            Не было передано ни одного поля на обновление.
        CoupleNotFoundException
            Если пара не найдена или пользователь не является её членом.
        """
        if update_dto.is_empty():
            raise NothingToUpdateException(detail="No fields provided for update.")

        if not await self._couple_repo.update_one(
            FilterOneCoupleDTO(id=couple_id, user_id=user_id),
            update_dto,
            PublicAccessContext(),
        ):
            raise CoupleNotFoundException(
                detail=f"Couple request with id={couple_id} not found.",
            )
