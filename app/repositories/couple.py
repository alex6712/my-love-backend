from uuid import UUID

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import CoupleRequestStatus
from app.models.couple import CoupleRequestModel
from app.repositories.interface import RepositoryInterface
from app.schemas.dto.couple import CoupleRequestDTO
from app.schemas.dto.user import PartnerDTO


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
    add_couple_request(initiator_id, recipient_id)
        Регистрация пары между пользователями.
    get_partner_by_user_id(user_id)
        Получение информации о партнёре пользователя.
    get_active_couple_by_partner_id(partner_id)
        Получение DTO пары по UUID одного из партнёров.
    get_active_couples_by_partner_ids(*partner_ids)
        Получение списка активных пар по UUID нескольких партнёров.
    find_existing_request(initiator_id, recipient_id)
        Поиск существующего запроса на создание пары.
    get_pending_requests_for_recipient(recipient_id)
        Получение входящих запросов для пользователя.
    update_request_status_by_id_and_recipient_id(couple_request_id, recipient_id, new_status)
        Обновление статуса входящего запроса на создание пары.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    def add_couple_request(self, initiator_id: UUID, recipient_id: UUID) -> None:
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
                status=CoupleRequestStatus.PENDING,
            )
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
            select(CoupleRequestModel).where(
                CoupleRequestModel.status == CoupleRequestStatus.ACCEPTED,
                or_(
                    CoupleRequestModel.initiator_id == user_id,
                    CoupleRequestModel.recipient_id == user_id,
                ),
            )
        )

        if couple is None:
            return None

        return (
            couple.initiator_id
            if couple.recipient_id == user_id
            else couple.recipient_id
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
        couple = await self.get_active_couple_by_partner_id(user_id)

        if couple is None:
            return None

        return couple.initiator if couple.recipient.id == user_id else couple.recipient

    async def get_active_couple_by_partner_id(
        self, partner_id: UUID
    ) -> CoupleRequestDTO | None:
        """Получение DTO пары по UUID одного из партнёров.

        Parameters
        ----------
        partner_id : UUID
            UUID пользователя.

        Returns
        -------
        CoupleRequestDTO | None
            DTO пары между пользователем и его партнёром,
            None — если пользователь не состоит в паре.

        Raises
        ------
        MultipleActiveCouplesException
            Если для пользователя найдено более одной активной пары
            (нарушение целостности данных).
        """
        couples = await self.get_active_couples_by_partner_ids(partner_id)

        return couples[0] if couples else None

    async def get_active_couples_by_partner_ids(
        self, *partner_ids: UUID
    ) -> list[CoupleRequestDTO]:
        """Получение списка активных пар по UUID нескольких партнёров.

        Parameters
        ----------
        *partner_ids : UUID
            Список UUID пользователей.

        Returns
        -------
        list[CoupleRequestDTO]
            Список DTO активных пар, в которых состоит хотя бы один
            из переданных пользователей.
        """
        result = await self.session.scalars(
            select(CoupleRequestModel)
            .options(
                selectinload(CoupleRequestModel.initiator),
                selectinload(CoupleRequestModel.recipient),
            )
            .where(
                CoupleRequestModel.status == CoupleRequestStatus.ACCEPTED,
                or_(
                    CoupleRequestModel.initiator_id.in_(partner_ids),
                    CoupleRequestModel.recipient_id.in_(partner_ids),
                ),
            )
        )

        return [CoupleRequestDTO.model_validate(request) for request in result.all()]

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
        request = await self.session.scalar(
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
        requests = await self.session.scalars(
            select(CoupleRequestModel)
            .options(
                selectinload(CoupleRequestModel.initiator),
                selectinload(CoupleRequestModel.recipient),
            )
            .where(
                CoupleRequestModel.status == CoupleRequestStatus.PENDING,
                CoupleRequestModel.recipient_id == recipient_id,
            )
        )

        return [CoupleRequestDTO.model_validate(request) for request in requests.all()]

    async def get_pending_request_by_id_and_recipient_id(
        self, couple_request_id: UUID, recipient_id: UUID
    ) -> CoupleRequestDTO | None:
        """Получение входящего запроса на создание пары по его ID и ID реципиента.

        Возвращает приглашение, если оно существует, адресовано указанному
        пользователю и находится в состоянии `CoupleRequestStatus.PENDING`.

        Parameters
        ----------
        couple_request_id : UUID
            UUID запроса на создание пары.
        recipient_id : UUID
            UUID пользователя-реципиента.

        Returns
        -------
        CoupleRequestDTO | None
            DTO запроса на создание пары, или None, если запрос не найден.
        """
        request = await self.session.scalar(
            select(CoupleRequestModel)
            .options(
                selectinload(CoupleRequestModel.initiator),
                selectinload(CoupleRequestModel.recipient),
            )
            .where(
                CoupleRequestModel.id == couple_request_id,
                CoupleRequestModel.recipient_id == recipient_id,
                CoupleRequestModel.status == CoupleRequestStatus.PENDING,
            )
        )

        return CoupleRequestDTO.model_validate(request) if request else None

    async def update_request_status_by_id_and_recipient_id(
        self,
        couple_request_id: UUID,
        recipient_id: UUID,
        new_status: CoupleRequestStatus,
    ) -> bool:
        """Обновление статуса входящего запроса на создание пары.

        Обновляет статус запроса только если он существует, адресован
        указанному реципиенту и находится в состоянии `CoupleRequestStatus.PENDING`.

        Parameters
        ----------
        couple_request_id : UUID
            UUID запроса на создание пары.
        recipient_id : UUID
            UUID пользователя-реципиента.
        new_status : CoupleRequestStatus
            Новый статус запроса.

        Returns
        -------
        bool
            True, если запись была обновлена, False — если запрос не найден
            или не находится в состоянии PENDING.
        """
        updated = await self.session.scalar(
            update(CoupleRequestModel)
            .where(
                CoupleRequestModel.id == couple_request_id,
                CoupleRequestModel.recipient_id == recipient_id,
                CoupleRequestModel.status == CoupleRequestStatus.PENDING,
            )
            .values(status=new_status)
            .returning(CoupleRequestModel.id)
        )

        return updated is not None
