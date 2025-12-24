from typing import Annotated

from fastapi import APIRouter, File, UploadFile, status

from app.core.dependencies.auth import StrictAuthenticationDependency
from app.core.dependencies.services import MediaServiceDependency
from app.schemas.dto.album import AlbumDTO
from app.schemas.v1.requests.create_album import CreateAlbumRequest
from app.schemas.v1.responses.albums import AlbumsResponse
from app.schemas.v1.responses.standard import StandardResponse

router = APIRouter(
    prefix="/media",
    tags=["media"],
)


@router.get(
    "/albums",
    response_model=AlbumsResponse,
    status_code=status.HTTP_200_OK,
    summary="Получение списка всех доступных пользователю медиа альбомов.",
)
async def get_albums(
    media_service: MediaServiceDependency,
    payload: StrictAuthenticationDependency,
) -> AlbumsResponse:
    """Получение списка всех доступных пользователю медиа альбомов.

    Возвращает список всех медиа альбомов, для которых установлено,
    что они доступны пользователю с UUID, переданным в токене доступа.

    Parameters
    ----------
    media_service : MediaServiceDependency
        Зависимость сервиса работы с медиа.
    payload : Payload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    AlbumsResponse
        Список всех доступных пользователю медиа альбомов.
    """
    albums: list[AlbumDTO] = await media_service.get_albums(payload["sub"])

    return AlbumsResponse(albums=albums, detail=f"Found {len(albums)} albums.")


@router.post(
    "/albums",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новый медиа альбом.",
)
async def post_albums(
    form_data: CreateAlbumRequest,
    media_service: MediaServiceDependency,
    payload: StrictAuthenticationDependency,
) -> StandardResponse:
    """Создание нового медиа альбома.

    Создаёт новую запись в базе данных, устанавливая переданные в теле
    запроса атрибуты.

    Parameters
    ----------
    form_data : CreateAlbumRequest
        Зависимость для получения данных из формы.
    media_service : MediaServiceDependency
        Зависимость сервиса работы с медиа.
    payload : Payload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    StandardResponse
        Успешный ответ о создании нового альбома.
    """
    await media_service.create_album(
        title=form_data.title,
        description=form_data.description,
        cover_url=form_data.cover_url,
        is_private=form_data.is_private,
        created_by=payload["sub"],
    )

    return StandardResponse(detail="New album created successfully.")


@router.post(
    "/upload",
    response_model=StandardResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Загрузка медиа-файлов в приватное хранилище.",
)
async def upload(
    file: Annotated[UploadFile, File(...)],
    media_service: MediaServiceDependency,
    payload: StrictAuthenticationDependency,
) -> StandardResponse:
    """TODO: Документация."""
    await media_service.upload_file(file, payload["sub"])

    return StandardResponse(detail="File uploaded successfully.")
