from fastapi import APIRouter, status

from app.core.dependencies.auth import StrictAuthenticationDependency
from app.core.dependencies.services import UsersServiceDependency
from app.schemas.dto.user import PartnerDTO
from app.schemas.v1.requests.create_couple import CreateCoupleRequest
from app.schemas.v1.responses.partner import PartnerResponse, StandardResponse

router = APIRouter(
    prefix="/users",
    tags=["users"],
)


@router.get(
    "/partner",
    response_model=PartnerResponse,
    status_code=status.HTTP_200_OK,
    summary="Получение информации о партнёре пользователя.",
)
async def get_partner(
    users_service: UsersServiceDependency,
    payload: StrictAuthenticationDependency,
) -> PartnerResponse:
    """Запрос на получение информации о партнёре пользователя.

    Проверяет наличие пары у пользователя и при нахождении возвращает
    информацию о партнёре.

    Parameters
    ----------
    users_service : UsersServiceDependency
        Зависимость сервиса пользователей.
    payload : StrictAuthenticationDependency
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    PartnerResponse
        Ответ с вложенным DTO партнёра.
    """
    partner: PartnerDTO | None = await users_service.get_partner(payload["sub"])

    return PartnerResponse(
        partner=partner,
        message="Partner found." if partner else "Partner not found.",
    )


@router.post(
    "/couple",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация информации о новой паре между пользователями.",
)
async def post_couple(
    form_data: CreateCoupleRequest,
    users_service: UsersServiceDependency,
    payload: StrictAuthenticationDependency,
) -> StandardResponse:
    """Запрос на регистрацию новой пары между пользователями.

    Регистрирует новую пару по UUID партнёра из `form_data` и UUID
    пользователя из токена доступа.

    Parameters
    ----------
    form_data : CreateCoupleRequest
        Зависимость для получения данных из формы.
    users_service : UsersServiceDependency
        Зависимость сервиса пользователей.
    payload : StrictAuthenticationDependency
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    StandardResponse
        Ответ, подтверждающий успешную регистрацию пары.
    """
    await users_service.register_couple(payload["sub"], form_data.partner_id)

    return StandardResponse(
        code=status.HTTP_201_CREATED,
        message="Couple register successfully.",
    )
