from fastapi import APIRouter, status

from app.core.dependencies.auth import StrictAuthenticationDependency
from app.core.dependencies.services import ServiceManagerDependency
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
    services: ServiceManagerDependency,
    payload: StrictAuthenticationDependency,
) -> UserResponse:
    """Запрос на получение информации о пользователе.

    Получает payload токена из зависимости на авторизацию, после
    чего возвращает данные о пользователе по UUID в `sub`.

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
    UserResponse
        Ответ с вложенным DTO пользователя.
    """
    user = await services.user.get_me(payload.sub)

    return UserResponse(
        user=user,
        detail="Current access token user's data.",
    )
