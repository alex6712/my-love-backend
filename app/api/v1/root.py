from fastapi import APIRouter, status

from app.core.dependencies.settings import SettingsDependency
from app.schemas.v1.responses.app_info import AppInfoResponse
from app.schemas.v1.responses.standard import StandardResponse

router = APIRouter(
    tags=["root"],
)


@router.get(
    "/health",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Проверка работоспособности API.",
    response_description="API работает",
)
async def health() -> StandardResponse:
    """Путь для проверки работоспособности API.

    Ничего не делает, кроме как возвращает положительный ответ на запрос.

    Returns
    -------
    StandardResponse
        Ответ о корректной работе сервера.
    """
    return StandardResponse(detail="API works!")


@router.get(
    "/app_info",
    response_model=AppInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Получение информации о приложении.",
    response_description="Информация о приложении",
)
async def app_info(settings: SettingsDependency) -> AppInfoResponse:
    """Запрос на получение информации о серверной стороне приложения.

    Получаемая информация:
    - app_name: str, имя приложения;
    - app_version: str, версия приложения;
    - app_description: str, полное описание приложения;
    - app_summary: str, краткое описание приложения;
    - admin_name: str, полное имя ответственного лица;
    - admin_email: str, адрес электронной почты для связи с ответственным лицом.

    Parameters
    ----------
    settings : Settings
        Настройки приложения.

    Returns
    -------
    AppInfoResponse
        Ответ, содержащий информацию о серверной стороне приложения.
    """
    return AppInfoResponse(
        app_name=settings.APP_NAME,
        app_version=settings.APP_VERSION,
        app_description=settings.APP_DESCRIPTION,
        app_summary=settings.APP_SUMMARY,
        admin_name=settings.ADMIN_NAME,
        admin_email=settings.ADMIN_EMAIL,
    )
