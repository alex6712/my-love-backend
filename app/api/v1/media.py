from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Path, status

from app.core.dependencies.auth import StrictAuthenticationDependency
from app.core.dependencies.services import MediaServiceDependency
from app.core.dependencies.transport import UploadFileDependency
from app.schemas.dto.album import AlbumDTO, AlbumWithItemsDTO
from app.schemas.v1.requests.attach_files import AttachFilesRequest
from app.schemas.v1.requests.create_album import CreateAlbumRequest
from app.schemas.v1.requests.upload_file import UploadFileRequest
from app.schemas.v1.responses.albums import AlbumResponse, AlbumsResponse
from app.schemas.v1.responses.standard import StandardResponse
from app.schemas.v1.responses.urls import PresignedURLResponse

router = APIRouter(
    prefix="/media",
    tags=["media"],
)


@router.post(
    "/upload/proxy",
    response_model=StandardResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Загрузка медиа-файлов в приватное хранилище.",
)
async def upload_proxy(
    form_data: UploadFileDependency,
    media_service: MediaServiceDependency,
    payload: StrictAuthenticationDependency,
) -> StandardResponse:
    """Загрузка медиа-файла в приватное хранилище.

    Позволяет пользователю загрузить медиа-файл в приватное хранилище.
    Необходимы права на выполнение операции загрузки и соответствующие данные о файле.

    Parameters
    ----------
    form_data : UploadFileDependency
        Зависимость для получения данных из формы, содержащих информацию о загружаемом файле.
    media_service : MediaServiceDependency
        Зависимость сервиса работы с медиа.
    payload : Payload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    StandardResponse
        Успешный ответ о загрузке файла.
        Возвращает сообщение об успешной загрузке файла и детальную информацию.
    """
    await media_service.upload_file(
        form_data.file,
        form_data.title,
        form_data.description,
        payload["sub"],
    )

    return StandardResponse(detail="File uploaded successfully.")


@router.post(
    "/upload/direct",
    response_model=PresignedURLResponse,
    status_code=status.HTTP_200_OK,
    summary="Получение presigned-url для загрузки медиа-файлов в приватное хранилище.",
)
async def upload_direct(
    form_data: UploadFileRequest,
    media_service: MediaServiceDependency,
    payload: StrictAuthenticationDependency,
) -> PresignedURLResponse:
    """Получение presigned-url для загрузки медиа-файлов в приватное хранилище.

    Предоставляет подписанную ссылку для прямой загрузки файла в объектное
    хранилище.
    Необходимы права на выполнение операции загрузки и соответствующие данные о файле.

    Parameters
    ----------
    form_data : UploadFileRequest
        Зависимость для получения данных из формы, содержащих информацию о загружаемом файле.
    media_service : MediaServiceDependency
        Зависимость сервиса работы с медиа.
    payload : Payload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    PresignedURLResponse
        Успешный ответ о генерации presigned-url.
    """
    presigned_url: str = await media_service.get_upload_presigned_url(
        form_data.content_type,
        form_data.title,
        form_data.description,
        payload["sub"],
    )

    return PresignedURLResponse(
        presigned_url=presigned_url,
        detail="File uploaded successfully.",
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

    return AlbumsResponse(albums=albums, detail=f"Found {len(albums)} album entries.")


@router.post(
    "/albums",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новый медиа альбом.",
)
async def post_albums(
    form_data: Annotated[
        CreateAlbumRequest, Body(description="Схема получения данных о медиа альбоме.")
    ],
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


@router.get(
    "/albums/{album_id}",
    response_model=AlbumResponse,
    status_code=status.HTTP_200_OK,
    summary="Получение подробной информации о медиа-альбоме.",
)
async def get_album(
    album_id: Annotated[UUID, Path(description="UUID запрашиваемого альбома.")],
    media_service: MediaServiceDependency,
    payload: StrictAuthenticationDependency,
) -> AlbumResponse:
    """Получение подробной информации о медиа-альбоме.

    Возвращает подробный DTO с полной информацией о конкретном
    медиа альбоме, чей UUID был передан.

    Если текущий пользователь не имеет доступа к этому альбому
    или альбом с переданным UUID не существует, будет
    возвращена ошибка.

    Parameters
    ----------
    media_service : MediaServiceDependency
        Зависимость сервиса работы с медиа.
    payload : Payload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    AlbumResponse
        Подробная информация о конкретном медиа-альбоме.
    """
    album: AlbumWithItemsDTO = await media_service.get_album(album_id, payload["sub"])

    return AlbumResponse(
        album=album, detail=f"Found album with {len(album.items)} files."
    )


@router.delete(
    "/albums/{album_id}",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Удаление медиа альбома по его UUID.",
)
async def delete_albums(
    album_id: Annotated[UUID, Path(description="UUID медиа альбома к удалению.")],
    media_service: MediaServiceDependency,
    payload: StrictAuthenticationDependency,
) -> StandardResponse:
    """Удаление медиа альбома по его UUID.

    Проверяет права владения текущего пользователя над альбомом с
    переданным UUID, удаляет его при достатке прав.

    Parameters
    ----------
    album_id : UUID
        UUID альбома к удалению.
    media_service : MediaServiceDependency
        Зависимость сервиса работы с медиа.
    payload : Payload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    StandardResponse
        Ответ о результате удаления медиа альбома.
    """
    await media_service.delete_album(album_id, payload["sub"])

    return StandardResponse(detail="Album entry deleted successfully.")


@router.patch(
    "/albums/{album_id}/attach",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Привязка медиа-файлов к альбому.",
)
async def attach(
    album_id: Annotated[
        UUID, Path(description="UUID альбома, в который добавляются файлы.")
    ],
    form_data: Annotated[
        AttachFilesRequest, Body(description="Список UUID медиа файлов к добавлению.")
    ],
    media_service: MediaServiceDependency,
    payload: StrictAuthenticationDependency,
) -> StandardResponse:
    """Привязка медиа-файлов к медиа-альбому.

    Получает в теле запроса список UUID медиа-файлов, которые
    будут добавлены в медиа альбом.

    album_id : UUID
        UUID альбома, к которому добавляются медиа-файлы.
    form_data : AttachMediaRequest
        Список UUID медиа-файлов к добавлению.
    media_service : MediaServiceDependency
        Зависимость сервиса работы с медиа.
    payload : Payload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    StandardResponse
        Ответ о результате добавления файлов к альбому.
    """
    await media_service.attach(album_id, form_data.files_uuids, payload["sub"])

    return StandardResponse(detail="Files successfully attached to album.")
