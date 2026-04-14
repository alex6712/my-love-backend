from typing import Annotated

from fastapi import APIRouter, Body, status

from app.core.dependencies.auth import StrictAuthenticationDependency
from app.core.dependencies.services import ServiceManagerDependency
from app.core.docs import AUTHORIZATION_ERROR_REF
from app.schemas.dto.user import PatchProfileDTO
from app.schemas.v1.requests.users import PatchProfileRequest
from app.schemas.v1.responses.standard import StandardResponse
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


@router.get(
    "/password-policy",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Получение информации о политиках валидации паролей.",
    response_description="Информация о политиках валидации паролей",
)
async def get_password_policy() -> StandardResponse:
    """Запрос на получение информации о политиках валидации паролей.

    Находится в разработке.

    Возвращает структурированный ответ об используемых политиках валидации
    пользовательских паролей. Не требует аутентификации, т.к. является
    внешним контрактом.

    Returns
    -------
    StandardResponse
        Ответ с информацией о политиках валидации паролей.
    """
    return StandardResponse(detail="Now in development.")


@router.patch(
    "/profile",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Редактирование профиля пользователя.",
    response_description="Профиль пользователя изменён успешно",
    responses={401: AUTHORIZATION_ERROR_REF},
)
async def patch_profile(
    body: Annotated[
        PatchProfileRequest,
        Body(description="Схема частичного обновления профиля пользователя."),
    ],
    services: ServiceManagerDependency,
    payload: StrictAuthenticationDependency,
) -> StandardResponse:
    """Запрос на редактирование профиля пользователя.

    Получает только изменённые данные профиля в `body`, сохраняет
    эти данные для авторизованного с помощью токена пользователя.

    Parameters
    ----------
    body : PatchProfileRequest
        Схема частичного обновления данных профиля пользователя.
        Содержит только те поля, которые нужно обновить.
    services : ServiceManager
        Менеджер сервисов уровня запроса (request-scoped).

        Предоставляет доступ к бизнес-сервисам приложения
        (например, auth, user, note, file и др.) через единый
        контейнер зависимостей.
    payload : AccessTokenPayload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    StandardResponse
        Ответ об успешном изменении профиля.
    """
    await services.user.update_profile(
        PatchProfileDTO.from_request_schema(body),
        payload.sub,
    )

    return StandardResponse(detail="User's profile updated successfully.")
