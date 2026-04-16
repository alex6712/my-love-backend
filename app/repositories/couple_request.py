from datetime import datetime
from uuid import UUID

from sqlalchemy import insert, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.core.enums import CoupleRequestStatus
from app.core.exceptions.couple import (
    CoupleNotSelfException,
    CoupleRequestAlreadyExistsException,
)
from app.infrastructure.postgresql import get_constraint_name
from app.models.couple_request import CoupleRequestModel
from app.repositories.interface import RepositoryInterface
from app.schemas.dto.couple import CoupleRequestDTO


class CoupleRequestRepository(RepositoryInterface):
    """Репозиторий запросов на создание пар между пользователями.

    Реализация паттерна Репозиторий. Является объектом доступа к данным (DAO).
    Реализует основные CRUD операции с парами пользователей.

    Attributes
    ----------
    session : AsyncSession
        Объект асинхронной сессии запроса.

    Methods
    -------
    add_couple_request(initiator_id, recipient_id)
        Создание запроса на регистрацию пары между пользователями.
    get_pending_requests_for_recipient(recipient_id)
        Получение входящих запросов для пользователя.
    update_request_status_by_id_and_recipient_id(couple_request_id, recipient_id, new_status)
        Обновление статуса входящего запроса на создание пары.
    """

    async def add_couple_request(self, initiator_id: UUID, recipient_id: UUID) -> None:
        """Создание запроса на регистрацию пары между пользователями.

        Добавляет в базу данных запись о новом запросе на создание пары между пользователями.
        Изначально этот запрос имеет статус `Couple.Status.PENDING`, пока реципиент не подтвердит
        приглашение инициатора.

        Parameters
        ----------
        initiator_id : UUID
            UUID пользователя-инициатора.
        recipient_id : UUID
            UUID пользователя-реципиента.
        """
        try:
            await self.session.scalar(
                insert(CoupleRequestModel).values(
                    initiator_id=initiator_id,
                    recipient_id=recipient_id,
                    status=CoupleRequestStatus.PENDING,
                )
            )
        except IntegrityError as e:
            constraint = get_constraint_name(e)

            if constraint == "uq_couple_request_pending":
                raise CoupleRequestAlreadyExistsException(
                    detail=f"Pending request from {initiator_id} to {recipient_id} already exists!"
                ) from e
            elif constraint == "ck_couple_not_self":
                raise CoupleNotSelfException(
                    detail="Cannot register couple with yourself!"
                ) from e

            raise

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
                or_(
                    CoupleRequestModel.initiator_id.in_(partner_ids),
                    CoupleRequestModel.recipient_id.in_(partner_ids),
                ),
                CoupleRequestModel.status == CoupleRequestStatus.ACCEPTED,
            )
        )

        return [CoupleRequestDTO.model_validate(request) for request in result.all()]

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
                CoupleRequestModel.recipient_id == recipient_id,
                CoupleRequestModel.status == CoupleRequestStatus.PENDING,
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
        accepted_at: datetime,
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
        accepted_at : datetime
            Дата и время принятия запроса.

        Returns
        -------
        bool
            True, если запись была обновлена, False - если запрос не найден
            или не находится в состоянии PENDING.
        """
        updated = await self.session.scalar(
            update(CoupleRequestModel)
            .where(
                CoupleRequestModel.id == couple_request_id,
                CoupleRequestModel.recipient_id == recipient_id,
                CoupleRequestModel.status == CoupleRequestStatus.PENDING,
            )
            .values(status=new_status, accepted_at=accepted_at)
            .returning(CoupleRequestModel.id)
        )

        return updated is not None
