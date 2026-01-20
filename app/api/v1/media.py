from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Path, Query, status

from app.core.dependencies.auth import StrictAuthenticationDependency
from app.core.dependencies.services import MediaServiceDependency
from app.core.dependencies.transport import (
    IdempotencyKeyDependency,
    UploadFileDependency,
)
from app.core.docs import AUTHORIZATION_ERROR_EXAMPLES
from app.schemas.dto.album import AlbumDTO, AlbumWithItemsDTO
from app.schemas.v1.requests.attach_files import AttachFilesRequest
from app.schemas.v1.requests.confirm_upload import ConfirmUploadRequest
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
    response_description="Загрузка завершена успешно",
    responses={401: AUTHORIZATION_ERROR_EXAMPLES},
)
async def upload_proxy(
    form_data: UploadFileDependency,
    media_service: MediaServiceDependency,
    payload: StrictAuthenticationDependency,
    idempotency_key: IdempotencyKeyDependency,
) -> StandardResponse:
    """Загрузка медиа-файла в приватное хранилище.

    Позволяет пользователю загрузить медиа-файл в приватное хранилище.
    Необходимы права на выполнение операции загрузки, соответствующие данные о файле
    и ключ идемпотентности.

    Parameters
    ----------
    form_data : UploadFileRequestForm
        Зависимость для получения данных из формы, содержащих информацию о загружаемом файле.
    media_service : MediaService
        Зависимость сервиса работы с медиа.
    payload : Payload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.
    idempotency_key : UUID
        Ключ идемпотентности. Получен из заголовков запроса.

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
        idempotency_key,
    )

    return StandardResponse(detail="File uploaded successfully.")


@router.post(
    "/upload/direct",
    response_model=PresignedURLResponse,
    status_code=status.HTTP_200_OK,
    summary="Получение Presigned URL для загрузки медиа-файлов в приватное хранилище.",
    response_description="URL для прямой загрузки получена успешно",
    responses={401: AUTHORIZATION_ERROR_EXAMPLES},
)
async def upload_direct(
    form_data: Annotated[
        UploadFileRequest,
        Body(description="Схема получения метаданных загружаемого медиа-файла."),
    ],
    media_service: MediaServiceDependency,
    payload: StrictAuthenticationDependency,
    idempotency_key: IdempotencyKeyDependency,
) -> PresignedURLResponse:
    """Получение presigned-url для загрузки медиа-файлов в приватное хранилище.

    Предоставляет подписанную ссылку для прямой загрузки файла в объектное
    хранилище.
    Необходимы права на выполнение операции загрузки, соответствующие данные о файле
    и ключ идемпотентности.

    Parameters
    ----------
    form_data : UploadFileRequest
        Зависимость для получения данных из формы, содержащих информацию о загружаемом файле.
    media_service : MediaService
        Зависимость сервиса работы с медиа.
    payload : Payload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.
    idempotency_key : UUID
        Ключ идемпотентности. Получен из заголовков запроса.

    Returns
    -------
    PresignedURLResponse
        Успешный ответ о генерации presigned-url.
    """
    file_id, presigned_url = await media_service.get_upload_presigned_url(
        form_data.content_type,
        form_data.title,
        form_data.description,
        payload["sub"],
        idempotency_key,
    )

    return PresignedURLResponse(
        file_id=file_id,
        presigned_url=presigned_url,
        detail="Presigned URL generated successfully.",
    )


@router.post(
    "/upload/confirm",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Подтверждение окончания загрузки файла по Presigned URL.",
    response_description="Завершение загрузки подтверждено",
    responses={401: AUTHORIZATION_ERROR_EXAMPLES},
)
async def upload_confirm(
    form_data: Annotated[
        ConfirmUploadRequest,
        Body(description="Схема получения UUID медиа-файла для подтверждения загрузки"),
    ],
    media_service: MediaServiceDependency,
    payload: StrictAuthenticationDependency,
) -> StandardResponse:
    """Подтверждение окончания загрузки файла по Presigned URL.

    Подтверждает загрузку файла по прямой ссылке в объектное хранилище.
    Проверяет, что пользователь завершил загрузку, права пользователя на
    владение загруженным файлом и корректность ключа идемпотентности.

    Parameters
    ----------
    form_data : ConfirmUploadRequest
        Зависимость для получения данных из формы.
    media_service : MediaService
        Зависимость сервиса работы с медиа.
    payload : Payload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    StandardResponse
        Успешный ответ о регистрации загруженного файла.
    """
    await media_service.confirm_upload(form_data.file_id, payload["sub"])

    return StandardResponse(detail="Upload confirmation is successful.")


@router.get(
    "/download/{file_id}/direct",
    response_model=PresignedURLResponse,
    status_code=status.HTTP_200_OK,
    summary="Получение Presigned URL для получения медиа-файлов из приватного хранилища.",
    response_description="URL для прямой загрузки получена успешно",
    responses={401: AUTHORIZATION_ERROR_EXAMPLES},
)
async def download_direct(
    file_id: Annotated[
        UUID,
        Path(description="UUID файла для загрузки на клиент."),
    ],
    media_service: MediaServiceDependency,
    payload: StrictAuthenticationDependency,
) -> PresignedURLResponse:
    """Получение presigned-url для загрузки медиа-файлов в приватное хранилище.

    Предоставляет подписанную ссылку для прямой загрузки файла в объектное
    хранилище.
    Необходимы права на выполнение операции загрузки, соответствующие данные о файле
    и ключ идемпотентности.

    Parameters
    ----------
    file_id : UUID
        UUID файла для загрузки на клиент.
    media_service : MediaService
        Зависимость сервиса работы с медиа.
    payload : Payload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    PresignedURLResponse
        Успешный ответ о генерации presigned-url.
    """
    file_id, presigned_url = await media_service.get_download_presigned_url(
        file_id,
        payload["sub"],
    )

    return PresignedURLResponse(
        file_id=file_id,
        presigned_url=presigned_url,
        detail="Presigned URL generated successfully.",
    )


@router.get(
    "/albums",
    response_model=AlbumsResponse,
    status_code=status.HTTP_200_OK,
    summary="Получение списка всех доступных пользователю медиа альбомов.",
    response_description="Список всех доступных альбомов",
    responses={401: AUTHORIZATION_ERROR_EXAMPLES},
)
async def get_albums(
    media_service: MediaServiceDependency,
    payload: StrictAuthenticationDependency,
    offset: Annotated[
        int,
        Query(
            ge=0,
            le=100,
            description="Смещение от начала списка (количество пропускаемых альбомов)ю",
        ),
    ] = 0,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=50,
            description="Количество возвращаемых альбомов.",
        ),
    ] = 10,
) -> AlbumsResponse:
    """Получение списка всех доступных пользователю медиа альбомов с пагинацией.

    Возвращает список медиа альбомов, доступных пользователю с UUID, переданным в токене доступа.
    Поддерживает пагинацию для работы с большими объемами данных.

    Parameters
    ----------
    media_service : MediaService
        Зависимость сервиса работы с медиа.
    payload : Payload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.
    offset : int, optional
        Смещение от начала списка (количество пропускаемых альбомов).
    limit : int, optional
        Количество возвращаемых альбомов.

    Returns
    -------
    AlbumsResponse
        Объект ответа, содержащий список доступных пользователю медиа альбомов
        в пределах заданной пагинации и общее количество найденных альбомов.
    """
    albums: list[AlbumDTO] = await media_service.get_albums(
        offset, limit, payload["sub"]
    )

    return AlbumsResponse(albums=albums, detail=f"Found {len(albums)} album entries.")


@router.post(
    "/albums",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новый медиа альбом.",
    response_description="Медиа-альбом создан успешно",
    responses={401: AUTHORIZATION_ERROR_EXAMPLES},
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
    response_description="Информация о меди-альбоме вместе с его элементами",
    responses={401: AUTHORIZATION_ERROR_EXAMPLES},
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
    response_description="Медиа-альбом удалён успешно",
    responses={401: AUTHORIZATION_ERROR_EXAMPLES},
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
    response_description="Медиа-файлы добавлены в альбом",
    responses={401: AUTHORIZATION_ERROR_EXAMPLES},
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
