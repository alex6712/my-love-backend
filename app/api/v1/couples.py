from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, status

from app.core.dependencies.auth import StrictAuthenticationDependency
from app.core.dependencies.services import CouplesServiceDependency
from app.schemas.dto.couples import CoupleRequestDTO
from app.schemas.dto.users import PartnerDTO
from app.schemas.v1.requests.create_couple import CreateCoupleRequest
from app.schemas.v1.responses.couple import CoupleRequestsResponse
from app.schemas.v1.responses.partner import PartnerResponse
from app.schemas.v1.responses.standard import StandardResponse

router = APIRouter(
    prefix="/couples",
    tags=["couples"],
)


@router.get(
    "/partner",
    response_model=PartnerResponse,
    status_code=status.HTTP_200_OK,
    summary="Получение информации о партнёре пользователя.",
)
async def get_partner(
    couples_service: CouplesServiceDependency,
    payload: StrictAuthenticationDependency,
) -> PartnerResponse:
    """Запрос на получение информации о партнёре пользователя.

    Проверяет наличие пары у пользователя и при нахождении возвращает
    информацию о партнёре.

    Parameters
    ----------
    couples_service : CouplesServiceDependency
        Зависимость сервиса пар пользователей.
    payload : StrictAuthenticationDependency
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    PartnerResponse
        Ответ с вложенным DTO партнёра.
    """
    partner: PartnerDTO | None = await couples_service.get_partner(payload["sub"])

    return PartnerResponse(
        partner=partner,
        detail="Current access token user partner's data."
        if partner
        else "Partner not found.",
    )


@router.post(
    "/request",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Запрос на регистрацию новой пары между пользователями.",
)
async def create_couple_request(
    form_data: CreateCoupleRequest,
    couples_service: CouplesServiceDependency,
    payload: StrictAuthenticationDependency,
) -> StandardResponse:
    """Запрос на регистрацию новой пары между пользователями.

    Создаёт приглашение на регистрацию пары между текущим пользователем
    и пользователем, чей UUID указан в `form_data`.

    Parameters
    ----------
    form_data : CreateCoupleRequest
        Зависимость для получения данных из формы.
    couples_service : CouplesServiceDependency
        Зависимость сервиса пар пользователей.
    payload : StrictAuthenticationDependency
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    StandardResponse
        Ответ, подтверждающий успешную регистрацию приглашения в пару.
    """
    await couples_service.create_couple_request(payload["sub"], form_data.partner_id)

    return StandardResponse(detail="Couple request created successfully.")


@router.post(
    "/{couple_id}/accept",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Подтверждение регистрации новой пары между пользователями.",
)
async def accept_couple_request(
    couple_id: Annotated[
        UUID, Path(description="UUID принимаемого приглашения в пару.")
    ],
    couples_service: CouplesServiceDependency,
    payload: StrictAuthenticationDependency,
) -> StandardResponse:
    """Подтверждение регистрации новой пары между пользователями.

    Проверяет, валидно ли приглашение для текущего пользователя
    и принимает запрос на создание пары пользователей.

    Parameters
    ----------
    couple_id : UUID
        UUID запроса на создание пары.
    couples_service : CouplesServiceDependency
        Зависимость сервиса пар пользователей.
    payload : StrictAuthenticationDependency
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    StandardResponse
        Отчёт об успешном создании новой пары.
    """
    await couples_service.accept_couple_request(couple_id, payload["sub"])

    return StandardResponse(detail="Couple register successfully.")


@router.post(
    "/{couple_id}/decline",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Отказ регистрации новой пары между пользователями.",
)
async def decline_couple_request(
    couple_id: Annotated[
        UUID, Path(description="UUID отклоняемого приглашения в пару.")
    ],
    couples_service: CouplesServiceDependency,
    payload: StrictAuthenticationDependency,
) -> StandardResponse:
    """TODO: Документация."""
    return StandardResponse(detail="Couple register declined.")


@router.get(
    "/pending",
    response_model=CoupleRequestsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Получение списка текущих приглашений.",
)
async def get_couple_requests(
    couples_service: CouplesServiceDependency,
    payload: StrictAuthenticationDependency,
) -> CoupleRequestsResponse:
    """Получение списка текущих приглашений.

    Возвращает список всех запросов на создание пары (приглашений),
    для который верно, что UUID реципиента совпадает с UUID текущего
    пользователя.

    Parameters
    ----------
    couples_service : CouplesServiceDependency
        Зависимость сервиса пар пользователей.
    payload : StrictAuthenticationDependency
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    CoupleRequestsResponse
        Список всех запросов на создание пары текущего пользователя.
    """
    requests: list[CoupleRequestDTO] = await couples_service.get_couple_requests(
        payload["sub"]
    )

    return CoupleRequestsResponse(
        requests=requests,
        detail=f"Found {len(requests)} couple requests.",
    )
