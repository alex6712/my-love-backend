from fastapi import APIRouter, status

from app.core.dependencies.auth import StrictAuthenticationDependency
from app.core.dependencies.services import UserServiceDependency
from app.core.docs import AUTHORIZATION_ERROR_REF
from app.schemas.v1.responses.user import UserResponse

router = APIRouter(
    prefix="/users",
    tags=["users"],
)


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Получение информации о пользователе.",
    response_description="Информация о текущем пользователе",
    responses={401: AUTHORIZATION_ERROR_REF},
)
async def get_me(
    user_service: UserServiceDependency,
    payload: StrictAuthenticationDependency,
) -> UserResponse:
    """Запрос на получение информации о пользователе.

    Получает payload токена из зависимости на авторизацию, после
    чего возвращает данные о пользователе по UUID в `sub`.

    Parameters
    ----------
    user_service : UserService
        Зависимость сервиса пользователей.
    payload : Payload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    UserResponse
        Ответ с вложенным DTO пользователя.
    """
    user = await user_service.get_me(payload["sub"])

    return UserResponse(
        user=user,
        detail="Current access token user's data.",
    )
