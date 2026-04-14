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
    summary="Получение сводной информации для главной страницы.",
    response_description="Количество файлов и заметок пользователя",
)
async def get_dashboard(
    services: ServiceManagerDependency,
    payload: StrictAuthenticationDependency,
) -> DashboardResponse:
    """Получение агрегированных данных для главной страницы приложения.

    Этот эндпоинт возвращает:
    - Количество всех доступных пользователю медиа-файлов (`files_count`);
    - Количество заметок пользователя (`notes_count`).

    Данные формируются путём последовательного вызова методов соответствующих сервисов:
    - `services.file.count_files(user_id)` - возвращает количество медиа-файлов,
        включая файлы партнёра.
    - `services.note.count_notes(user_id)` - возвращает количество заметок пользователя.

    Используется кэш Redis при наличии (cash hit).

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
    DashboardResponse
        Объект с агрегированными данными для главной страницы пользователя.
    """
    user_id = payload.sub

    files_count = await services.file.count_files(user_id)
    notes_count = await services.note.count_notes(user_id)

    return DashboardResponse(
        files_count=files_count,
        notes_count=notes_count,
        detail="Data for dashboard aggregated successfully.",
    )
