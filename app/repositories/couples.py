from uuid import UUID

from sqlalchemy import ScalarResult, and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import CoupleRequestStatus
from app.models.couple import CoupleRequestModel
from app.repositories.interface import RepositoryInterface
from app.schemas.dto.couples import CoupleRequestDTO
from app.schemas.dto.users import PartnerDTO


class CouplesRepository(RepositoryInterface):
    """Репозиторий пар между пользователями.

    Реализация паттерна Репозиторий. Является объектом доступа к данным (DAO).
    Реализует основные CRUD операции с парами пользователей.

    Attributes
    ----------
    session : AsyncSession
        Объект асинхронной сессии запроса.

    Methods
    -------
    add_couple_request(initiator_id, recipient_id)
        Регистрация пары между пользователями.
    get_partner_by_user_id(user_id)
        Получение информации о партнёре пользователя.
    get_active_couple_by_partner_id(partner_id)
        Получение DTO пары по UUID одного из партнёров.
    find_existing_request(initiator_id, recipient_id)
        Поиск существующего запроса на создание пары.
    get_pending_requests_for_recipient(recipient_id)
        Получение входящих запросов для пользователя.
    update_request_status(request_id, status)
        Обновление статуса запроса на создание пары.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def add_couple_request(self, initiator_id: UUID, recipient_id: UUID) -> None:
        """Создание приглашения на регистрацию пары между пользователями.

        Добавляет в базу данных запись о новой паре между пользователями,
        изначально эта пара имеет статус `Couple.Status.PENDING`, пока реципиент не подтвердит
        приглашение инициатора.

        Parameters
        ----------
        initiator_id : UUID
            UUID пользователя-инициатора.
        recipient_id : UUID
            UUID пользователя-реципиента.
        """
        self.session.add(
            CoupleRequestModel(
                initiator_id=initiator_id,
                recipient_id=recipient_id,
                status=CoupleRequestStatus.PENDING.value,
            )
        )

    async def get_partner_by_user_id(self, user_id: UUID) -> PartnerDTO | None:
        """Получение информации о партнёре пользователя.

        Получает UUID пользователя, загружает информацию о паре,
        в которой этот пользователь состоит и возвращает DTO партнёра.

        Parameters
        ----------
        user_id : UUID
            UUID пользователя в системе.

        Returns
        -------
        PartnerDTO | None
            Сохранённая о партнёре пользователя информация:
            - PartnerDTO если партнёр найден;
            - None если партнёр не найден.
        """
        couple: CoupleRequestDTO | None = await self.get_active_couple_by_partner_id(
            user_id
        )

        if couple is None:
            return None

        return couple.initiator if couple.recipient.id == user_id else couple.recipient

    async def get_active_couple_by_partner_id(
        self, partner_id: UUID
    ) -> CoupleRequestDTO | None:
        """Получение DTO пары по UUID одного из партнёров.

        Получает на вход UUID одного из партнёров и ищет в базе данных
        запись о паре, в которой состоит данный пользователь.

        Parameters
        ----------
        partner_id : UUID
            UUID пользователя.

        Returns
        -------
        CoupleDTO | None
            DTO пары между пользователем и его партнёром, None - если пользователь не состоит в паре.
        """
        couple: CoupleRequestModel | None = await self.session.scalar(
            select(CoupleRequestModel)
            .options(
                selectinload(CoupleRequestModel.initiator),
                selectinload(CoupleRequestModel.recipient),
            )
            .where(
                and_(
                    CoupleRequestModel.status == CoupleRequestStatus.ACCEPTED.value,
                    or_(
                        CoupleRequestModel.initiator_id == partner_id,
                        CoupleRequestModel.recipient_id == partner_id,
                    ),
                ),
            )
        )

        return CoupleRequestDTO.model_validate(couple) if couple else None

    async def find_existing_request(
        self, initiator_id: UUID, recipient_id: UUID
    ) -> CoupleRequestDTO | None:
        """Поиск существующего запроса на создание пары.

        Получает на вход UUID инициатора и реципиента. Возвращает
        DTO приглашения или None.

        Parameters
        ----------
        initiator_id : UUID
            UUID пользователя-инициатора.
        recipient_id : UUID
            UUID пользователя-реципиента.

        Returns
        -------
        CoupleRequestDTO | None
            DTO запроса на создание пары или None, если такого не имеется.
        """
        request: CoupleRequestModel | None = await self.session.scalar(
            select(CoupleRequestModel)
            .options(
                selectinload(CoupleRequestModel.initiator),
                selectinload(CoupleRequestModel.recipient),
            )
            .where(
                or_(
                    and_(
                        CoupleRequestModel.initiator_id == initiator_id,
                        CoupleRequestModel.recipient_id == recipient_id,
                    ),
                    and_(
                        CoupleRequestModel.initiator_id == recipient_id,
                        CoupleRequestModel.recipient_id == initiator_id,
                    ),
                )
            )
        )

        return CoupleRequestDTO.model_validate(request) if request else None

    async def get_pending_requests_for_recipient(
        self, recipient_id: UUID
    ) -> list[CoupleRequestDTO]:
        """Получение входящих запросов для пользователя.

        Возвращает все приглашения пользователю с переданным UUID,
        которые находятся в состоянии `CoupleRequestStatus.PENDING`.

        Parameters
        ----------
        recipient_id : UUID
            UUID пользователя-реципиента.

        Returns
        -------
        list[CoupleRequestDTO]
            Список всех приглашений на создание пары.
        """
        requests: ScalarResult[CoupleRequestModel] = await self.session.scalars(
            select(CoupleRequestModel)
            .options(
                selectinload(CoupleRequestModel.initiator),
                selectinload(CoupleRequestModel.recipient),
            )
            .where(
                and_(
                    CoupleRequestModel.status == CoupleRequestStatus.PENDING.value,
                    CoupleRequestModel.recipient_id == recipient_id,
                )
            )
        )

        return [CoupleRequestDTO.model_validate(request) for request in requests.all()]

    async def update_request_status(
        self, request_id: UUID, status: CoupleRequestStatus
    ) -> None:
        """Обновление статуса запроса на создание пары.

        Получает на вход UUID запроса на создание пары и новый
        статус запроса. Обновляет запись в базе данных.

        Parameters
        ----------
        request_id : UUID
            UUID запроса на создание пары.
        status : CoupleRequestStatus
            Новый статус запроса.
        """
        await self.session.execute(
            update(CoupleRequestModel)
            .where(CoupleRequestModel.id == request_id)
            .values(status=status.value)
        )
