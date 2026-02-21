from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Path, Query, status

from app.core.dependencies.auth import StrictAuthenticationDependency
from app.core.dependencies.services import FileServiceDependency
from app.core.dependencies.transport import IdempotencyKeyDependency
from app.core.docs import AUTHORIZATION_ERROR_REF, IDEMPOTENCY_CONFLICT_ERROR_REF
from app.core.enums import SortOrder
from app.schemas.dto.file import FileMetadataDTO
from app.schemas.v1.requests.files import (
    ConfirmUploadRequest,
    DownloadFilesBatchRequest,
    PatchFileRequest,
    UploadFileRequest,
    UploadFilesBatchRequest,
)
from app.schemas.v1.responses.files import FilesResponse
from app.schemas.v1.responses.standard import StandardResponse
from app.schemas.v1.responses.urls import (
    PresignedURLResponse,
    PresignedURLsBatchResponse,
)

router = APIRouter(
    prefix="/files",
    tags=["media-files"],
    responses={401: AUTHORIZATION_ERROR_REF},
)


@router.get(
    "",
    response_model=FilesResponse,
    status_code=status.HTTP_200_OK,
    summary="Получение списка всех доступных пользователю медиа файлов.",
    response_description="Список всех доступных файлов",
)
async def get_files(
    file_service: FileServiceDependency,
    payload: StrictAuthenticationDependency,
    offset: Annotated[
        int,
        Query(
            ge=0,
            description="Смещение от начала списка (количество пропускаемых файлов).",
        ),
    ] = 0,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=50,
            description="Количество возвращаемых файлов.",
        ),
    ] = 10,
    order: Annotated[
        SortOrder,
        Query(
            description="Направление сортировки файлов.",
        ),
    ] = SortOrder.ASC,
) -> FilesResponse:
    """Получение списка всех доступных пользователю медиа файлов с пагинацией.

    Возвращает список медиа файлов, доступных пользователю с UUID, переданным в токене доступа.
    Поддерживает пагинацию для работы с большими объемами данных.

    Parameters
    ----------
    file_service : AlbumService
        Зависимость сервиса работы с файлами.
    payload : Payload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.
    offset : int, optional
        Смещение от начала списка (количество пропускаемых файлов).
    limit : int, optional
        Количество возвращаемых файлов.
    order : SortOrder, optional
        Направление сортировки файлов.

    Returns
    -------
    FilesResponse
        Объект ответа, содержащий список доступных пользователю медиа файлов
        в пределах заданной пагинации и общее количество найденных файлов.
    """
    files, total = await file_service.get_files(offset, limit, order, payload["sub"])

    return FilesResponse(
        files=files, total=total, detail=f"Found {total} file entries."
    )


@router.post(
    "/upload",
    response_model=PresignedURLResponse,
    status_code=status.HTTP_200_OK,
    summary="Получение Presigned URL для загрузки медиа-файла в приватное хранилище.",
    response_description="URL для прямой загрузки получена успешно",
    responses={400: IDEMPOTENCY_CONFLICT_ERROR_REF},
)
async def upload(
    body: Annotated[
        UploadFileRequest,
        Body(description="Схема получения метаданных загружаемого медиа-файла."),
    ],
    file_service: FileServiceDependency,
    payload: StrictAuthenticationDependency,
    idempotency_key: IdempotencyKeyDependency,
) -> PresignedURLResponse:
    """Получение presigned-url для загрузки медиа-файла в приватное хранилище.

    Предоставляет подписанную ссылку для прямой загрузки файла в объектное
    хранилище.
    Необходимы права на выполнение операции загрузки, соответствующие данные о файле
    и ключ идемпотентности.

    Parameters
    ----------
    body : UploadFileRequest
        Данные, полученные от клиента в теле запроса.
    file_service : FileService
        Зависимость сервиса работы с файлами.
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
    url = await file_service.get_upload_presigned_url(
        FileMetadataDTO.model_validate(body),
        payload["sub"],
        idempotency_key,
    )

    return PresignedURLResponse(
        url=url,
        detail="Presigned URL generated successfully.",
    )


@router.post(
    "/upload/batch",
    response_model=PresignedURLsBatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Получение Presigned URL для загрузки пакета медиа-файлов в приватное хранилище.",
    response_description="URLs для прямой загрузки получены успешно",
    responses={400: IDEMPOTENCY_CONFLICT_ERROR_REF},
)
async def upload_batch(
    body: Annotated[
        UploadFilesBatchRequest,
        Body(description="Схема получения метаданных загружаемых медиа-файлов."),
    ],
    file_service: FileServiceDependency,
    payload: StrictAuthenticationDependency,
    idempotency_key: IdempotencyKeyDependency,
) -> PresignedURLsBatchResponse:
    """Получение presigned-url для загрузки пакета медиа-файлов в приватное хранилище.

    Предоставляет подписанные ссылки для прямой загрузки нескольких файлов в объектное
    хранилище.
    Необходимы права на выполнение операции загрузки, соответствующие данные о файлах
    и ключ идемпотентности.

    Parameters
    ----------
    body : UploadFilesBatchRequest
        Данные, полученные от клиента в теле запроса.
    file_service : FileService
        Зависимость сервиса работы с файлами.
    payload : Payload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.
    idempotency_key : UUID
        Ключ идемпотентности. Получен из заголовков запроса.

    Returns
    -------
    PresignedURLsBatchResponse
        Успешный ответ о генерации presigned-url.
    """
    urls = await file_service.get_upload_presigned_urls(
        [FileMetadataDTO.model_validate(m) for m in body.files_metadata],
        payload["sub"],
        idempotency_key,
    )

    return PresignedURLsBatchResponse(
        urls=urls, detail="Presigned URLs generated successfully."
    )


@router.post(
    "/upload/confirm",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Подтверждение окончания загрузки файла по Presigned URL.",
    response_description="Завершение загрузки подтверждено",
)
async def upload_confirm(
    body: Annotated[
        ConfirmUploadRequest,
        Body(description="Схема получения UUID медиа-файла для подтверждения загрузки"),
    ],
    file_service: FileServiceDependency,
    payload: StrictAuthenticationDependency,
) -> StandardResponse:
    """Подтверждение окончания загрузки файла по Presigned URL.

    Подтверждает загрузку файла по прямой ссылке в объектное хранилище.
    Проверяет, что пользователь завершил загрузку, права пользователя на
    владение загруженным файлом и корректность ключа идемпотентности.

    Parameters
    ----------
    body : ConfirmUploadRequest
        Данные, полученные от клиента в теле запроса.
    file_service : FileService
        Зависимость сервиса работы с файлами.
    payload : Payload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    StandardResponse
        Успешный ответ о регистрации загруженного файла.
    """
    await file_service.confirm_upload(body.file_id, payload["sub"])

    return StandardResponse(detail="Upload confirmation is successful.")


@router.get(
    "/{file_id}/download",
    response_model=PresignedURLResponse,
    status_code=status.HTTP_200_OK,
    summary="Получение Presigned URL для получения медиа-файла из приватного хранилища.",
    response_description="URL для скачивания получена успешно",
)
async def download(
    file_id: Annotated[
        UUID,
        Path(description="UUID файла для скачивания на клиент."),
    ],
    file_service: FileServiceDependency,
    payload: StrictAuthenticationDependency,
) -> PresignedURLResponse:
    """Получение presigned-url для скачивания медиа-файла из приватного хранилища.

    Предоставляет подписанную ссылку для прямого скачивания файла из объектного
    хранилища.
    Необходимы права на выполнение операции скачивания.

    Parameters
    ----------
    file_id : UUID
        UUID файла для скачивания на клиент.
    file_service : FileService
        Зависимость сервиса работы с файлами.
    payload : Payload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    PresignedURLResponse
        Успешный ответ о генерации presigned-url для скачивания.
    """
    url = await file_service.get_download_presigned_url(
        file_id,
        payload["sub"],
    )

    return PresignedURLResponse(
        url=url,
        detail="Presigned URL generated successfully.",
    )


@router.get(
    "/download/batch",
    response_model=PresignedURLsBatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Получение Presigned URL для получения пакета медиа-файлов из приватного хранилища.",
    response_description="URLs для скачивания получены успешно",
)
async def download_batch(
    body: Annotated[
        DownloadFilesBatchRequest,
        Body(description="Схема получения UUID файлов для скачивания на клиент."),
    ],
    file_service: FileServiceDependency,
    payload: StrictAuthenticationDependency,
) -> PresignedURLsBatchResponse:
    """Получение presigned-url для скачивания пакета медиа-файлов в приватное хранилище.

    Предоставляет подписанные ссылки для прямого скачивания нескольких файлов из объектного
    хранилища на клиент.
    Необходимы права на выполнение операции скачивания.

    Parameters
    ----------
    body : DownloadFilesBatchRequest
        Данные, полученные от клиента в теле запроса.
    file_service : FileService
        Зависимость сервиса работы с файлами.
    payload : Payload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    PresignedURLsBatchResponse
        Успешный ответ о генерации presigned-urls для скачивания.
    """
    urls = await file_service.get_download_presigned_urls(
        body.files_uuids,
        payload["sub"],
    )

    return PresignedURLsBatchResponse(
        urls=urls,
        detail="Presigned URLs generated successfully.",
    )


@router.patch(
    "/{file_id}",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Частичное изменение атрибутов существующего медиа-файла.",
    response_description="Данные успешно изменены",
)
async def patch_file(
    file_id: Annotated[UUID, Path(description="UUID медиа файла к изменению.")],
    body: Annotated[
        PatchFileRequest,
        Body(description="Схема частичного обновления атрибутов файла"),
    ],
    file_service: FileServiceDependency,
    payload: StrictAuthenticationDependency,
) -> StandardResponse:
    """Частичное изменение медиа файла по его UUID.

    Проверяет права владения текущего пользователя над файлом с
    переданным UUID, изменяет только переданные атрибуты при достатке прав.
    Все поля в теле запроса опциональны — передаются только те атрибуты,
    которые необходимо изменить.

    Parameters
    ----------
    file_id : UUID
        UUID файла к изменению.
    body : PatchFileRequest
        Данные, полученные от клиента в теле запроса.
        Содержит только те поля, которые нужно обновить.
    file_service : FileServiceDependency
        Зависимость сервиса работы с файлами.
    payload : Payload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    StandardResponse
        Ответ о результате изменения медиа файла.
    """
    await file_service.update_file(
        file_id,
        body.title,
        body.description,
        payload["sub"],
    )

    return StandardResponse(detail="File info edited successfully.")


@router.delete(
    "/{file_id}",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Удаление медиа-файла из системы.",
    response_description="Файл удалён успешно",
)
async def delete_file(
    file_id: Annotated[
        UUID,
        Path(description="UUID файла для удаления."),
    ],
    file_service: FileServiceDependency,
    payload: StrictAuthenticationDependency,
) -> StandardResponse:
    """Удаление медиа-файла по его UUID.

    Удаляет файл по переданному UUID, что открепляет его от файла.
    Необходимы права на выполнение операции удаления.

    Parameters
    ----------
    file_id : UUID
        UUID файла для удаления.
    file_service : FileService
        Зависимость сервиса работы с файлами.
    payload : Payload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    StandardResponse
        Успешный ответ об удалении медиа-файла.
    """
    await file_service.delete_file(file_id, payload["sub"])

    return StandardResponse(detail="File deleted successfully.")
