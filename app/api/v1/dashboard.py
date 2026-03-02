import asyncio
from uuid import UUID

from fastapi import APIRouter, status

from app.core.dependencies.auth import StrictAuthenticationDependency
from app.core.dependencies.services import ServiceManagerDependency
from app.core.docs import AUTHORIZATION_ERROR_REF
from app.schemas.v1.responses.dashboard import DashboardResponse

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
    responses={401: AUTHORIZATION_ERROR_REF},
)


@router.get(
    "",
    response_model=DashboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Получение сводной информации для главной страницы",
    response_description="Количество фото и заметок пользователя",
)
async def get_dashboard(
    services: ServiceManagerDependency,
    payload: StrictAuthenticationDependency,
) -> DashboardResponse:
    """Получение агрегированных данных для главной страницы приложения.

    Этот эндпоинт возвращает:
    - Количество всех доступных пользователю медиа-файлов (`photos_count`);
    - Количество заметок пользователя (`notes_count`).

    Данные формируются путём параллельного вызова методов соответствующих сервисов,
    чтобы минимизировать задержку:
    - `services.file.count_files(user_id)` - возвращает количество медиа-файлов,
      включая файлы партнёра. Используется кэш Redis при наличии.
    - `services.note.count_notes(user_id)` - возвращает количество заметок пользователя.

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
    payload : Payload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    DashboardResponse
        Объект с агрегированными данными для главной страницы пользователя.
    """
    user_id: UUID = payload["sub"]

    files_count, notes_count = await asyncio.gather(
        services.file.count_files(user_id),
        services.note.count_notes(user_id),
    )

    return DashboardResponse(
        files_count=files_count,
        notes_count=notes_count,
        detail="Data for dashboard aggregated successfully.",
    )
