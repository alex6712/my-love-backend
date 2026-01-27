from fastapi import APIRouter, status
from fastapi.responses import PlainTextResponse

from app.core.dependencies.settings import SettingsDependency

api_root_router = APIRouter(
    include_in_schema=False,
)


@api_root_router.get(
    "/robots.txt",
    response_class=PlainTextResponse,
    status_code=status.HTTP_200_OK,
    summary="Получение файла robots.txt для ботов.",
    response_description="Файл robots.txt для API",
)
async def robots_txt(settings: SettingsDependency) -> str:
    """Получение файла robots.txt для ботов.

    Возвращает ответ с типом контента text/plain и текстом
    файла robots.txt.

    Returns
    -------
    str
        Текст файла robots.txt.
    """
    return settings.ROBOTS_CONTENT
