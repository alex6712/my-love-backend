from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Path, status

from app.core.dependencies.auth import StrictAuthenticationDependency
from app.core.dependencies.services import ServiceManagerDependency
from app.core.docs import AUTHORIZATION_ERROR_REF
from app.schemas.v1.requests.couples import CreateCoupleRequest
from app.schemas.v1.responses.couple import CoupleRequestsResponse
from app.schemas.v1.responses.partner import PartnerResponse
from app.schemas.v1.responses.standard import StandardResponse

router = APIRouter(
    prefix="/couples",
    tags=["couples"],
    responses={401: AUTHORIZATION_ERROR_REF},
)


@router.get(
    "/partner",
    response_model=PartnerResponse,
    status_code=status.HTTP_200_OK,
    summary="Получение информации о партнёре пользователя.",
    response_description="Информация о партнёре текущего пользователя",
)
async def get_partner(
    services: ServiceManagerDependency,
    payload: StrictAuthenticationDependency,
) -> PartnerResponse:
    """Запрос на получение информации о партнёре пользователя.

    Проверяет наличие пары у пользователя и при нахождении возвращает
    информацию о партнёре.

    Parameters
    ----------
    services : ServiceManager
        Менеджер сервисов уровня запроса (request-scoped).

        Предоставляет доступ к бизнес-сервисам приложения
        (например, auth, user, note, file и др.) через единый
        контейнер зависимостей.

        Гарантирует:
        - Использование одного экземпляра Unit of Work в рамках запроса;
        - Единый доступ к инфраструктурным зависимостям (Redis, S3 и др.);
        - Ленивую (lazy) инициализацию сервисов;
        - Отсутствие повторных инстансов одного и того же сервиса
          в пределах одного HTTP-запроса.
    payload : AccessTokenPayload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    PartnerResponse
        Ответ с вложенным DTO партнёра.
    """
    partner = await services.couple.get_partner(payload.sub)

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
    response_description="Запрос успешно отправлен",
)
async def create_couple_request(
    body: Annotated[
        CreateCoupleRequest,
        Body(description="Схема запроса на создание приглашения в пару."),
    ],
    services: ServiceManagerDependency,
    payload: StrictAuthenticationDependency,
) -> StandardResponse:
    """Запрос на регистрацию новой пары между пользователями.

    Создаёт приглашение на регистрацию пары между текущим пользователем
    и пользователем, чей username указан в `body`.

    Parameters
    ----------
    body : CreateCoupleRequest
        Данные, полученные от клиента в теле запроса.
    services : ServiceManager
        Менеджер сервисов уровня запроса (request-scoped).

        Предоставляет доступ к бизнес-сервисам приложения
        (например, auth, user, note, file и др.) через единый
        контейнер зависимостей.

        Гарантирует:
        - Использование одного экземпляра Unit of Work в рамках запроса;
        - Единый доступ к инфраструктурным зависимостям (Redis, S3 и др.);
        - Ленивую (lazy) инициализацию сервисов;
        - Отсутствие повторных инстансов одного и того же сервиса
          в пределах одного HTTP-запроса.
    payload : AccessTokenPayload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    StandardResponse
        Ответ, подтверждающий успешную регистрацию приглашения в пару.
    """
    await services.couple.create_couple_request(payload.sub, body.partner_username)

    return StandardResponse(detail="Couple request created successfully.")


@router.post(
    "/{couple_id}/accept",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Подтверждение регистрации новой пары между пользователями.",
    response_description="Регистрация пары подтверждена",
)
async def accept_couple_request(
    couple_id: Annotated[
        UUID, Path(description="UUID принимаемого приглашения в пару.")
    ],
    services: ServiceManagerDependency,
    payload: StrictAuthenticationDependency,
) -> StandardResponse:
    """Подтверждение регистрации новой пары между пользователями.

    Проверяет, валидно ли приглашение для текущего пользователя
    и принимает запрос на создание пары пользователей.

    Parameters
    ----------
    couple_id : UUID
        UUID запроса на создание пары.
    services : ServiceManager
        Менеджер сервисов уровня запроса (request-scoped).

        Предоставляет доступ к бизнес-сервисам приложения
        (например, auth, user, note, file и др.) через единый
        контейнер зависимостей.

        Гарантирует:
        - Использование одного экземпляра Unit of Work в рамках запроса;
        - Единый доступ к инфраструктурным зависимостям (Redis, S3 и др.);
        - Ленивую (lazy) инициализацию сервисов;
        - Отсутствие повторных инстансов одного и того же сервиса
          в пределах одного HTTP-запроса.
    payload : AccessTokenPayload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    StandardResponse
        Отчёт об успешном создании новой пары.
    """
    await services.couple.accept_couple_request(couple_id, payload.sub)

    return StandardResponse(detail="Couple register successfully.")


@router.post(
    "/{couple_id}/decline",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Отказ регистрации новой пары между пользователями.",
    response_description="В регистрации пары отказано",
)
async def decline_couple_request(
    couple_id: Annotated[
        UUID, Path(description="UUID отклоняемого приглашения в пару.")
    ],
    services: ServiceManagerDependency,
    payload: StrictAuthenticationDependency,
) -> StandardResponse:
    """Отклонение регистрации новой пары между пользователями.

    Проверяет, валидно ли приглашение для текущего пользователя
    и отклоняет запрос на создание пары пользователей.

    Parameters
    ----------
    couple_id : UUID
        UUID запроса на создание пары.
    services : ServiceManager
        Менеджер сервисов уровня запроса (request-scoped).

        Предоставляет доступ к бизнес-сервисам приложения
        (например, auth, user, note, file и др.) через единый
        контейнер зависимостей.

        Гарантирует:
        - Использование одного экземпляра Unit of Work в рамках запроса;
        - Единый доступ к инфраструктурным зависимостям (Redis, S3 и др.);
        - Ленивую (lazy) инициализацию сервисов;
        - Отсутствие повторных инстансов одного и того же сервиса
          в пределах одного HTTP-запроса.
    payload : AccessTokenPayload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    StandardResponse
        Отчёт об успешном отклонении запроса.
    """
    await services.couple.decline_couple_request(couple_id, payload.sub)

    return StandardResponse(detail="Couple register declined.")


@router.get(
    "/pending",
    response_model=CoupleRequestsResponse,
    status_code=status.HTTP_200_OK,
    summary="Получение списка текущих приглашений.",
    response_description="Список текущих приглашений в пару",
)
async def get_couple_requests(
    services: ServiceManagerDependency,
    payload: StrictAuthenticationDependency,
) -> CoupleRequestsResponse:
    """Получение списка текущих приглашений.

    Возвращает список всех запросов на создание пары (приглашений),
    для который верно, что UUID реципиента совпадает с UUID текущего
    пользователя.

    Parameters
    ----------
    services : ServiceManager
        Менеджер сервисов уровня запроса (request-scoped).

        Предоставляет доступ к бизнес-сервисам приложения
        (например, auth, user, note, file и др.) через единый
        контейнер зависимостей.

        Гарантирует:
        - Использование одного экземпляра Unit of Work в рамках запроса;
        - Единый доступ к инфраструктурным зависимостям (Redis, S3 и др.);
        - Ленивую (lazy) инициализацию сервисов;
        - Отсутствие повторных инстансов одного и того же сервиса
          в пределах одного HTTP-запроса.
    payload : AccessTokenPayload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    CoupleRequestsResponse
        Список всех запросов на создание пары текущего пользователя.
    """
    requests = await services.couple.get_couple_requests(payload.sub)

    detail = "Couple requests not found."
    if len(requests) > 0:
        detail = f"Found {len(requests)} couple requests."

    return CoupleRequestsResponse(requests=requests, detail=detail)
