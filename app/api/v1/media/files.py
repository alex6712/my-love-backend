from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Path, status

from app.core.dependencies.auth import StrictAuthenticationDependency
from app.core.dependencies.services import FilesServiceDependency
from app.core.dependencies.transport import (
    IdempotencyKeyDependency,
    UploadFileDependency,
)
from app.core.docs import AUTHORIZATION_ERROR_REF
from app.schemas.v1.requests.confirm_upload import ConfirmUploadRequest
from app.schemas.v1.requests.upload_file import UploadFileRequest
from app.schemas.v1.responses.standard import StandardResponse
from app.schemas.v1.responses.urls import PresignedURLResponse

router = APIRouter(
    prefix="/files",
    tags=["media-files"],
)


@router.post(
    "/upload/proxy",
    response_model=StandardResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Загрузка медиа-файлов в приватное хранилище.",
    response_description="Загрузка завершена успешно",
    responses={401: AUTHORIZATION_ERROR_REF},
)
async def upload_proxy(
    form_data: UploadFileDependency,
    file_service: FilesServiceDependency,
    payload: StrictAuthenticationDependency,
    idempotency_key: IdempotencyKeyDependency,
) -> StandardResponse:
    """Загрузка медиа-файла в приватное хранилище через прокси.

    Позволяет пользователю загрузить медиа-файл в приватное хранилище.
    Необходимы права на выполнение операции загрузки, соответствующие данные о файле
    и ключ идемпотентности.

    Parameters
    ----------
    form_data : UploadFileRequestForm
        Зависимость для получения данных из формы, содержащих информацию о загружаемом файле.
    file_service : FilesService
        Зависимость сервиса работы с файлами.
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
    await file_service.upload_file(
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
    responses={401: AUTHORIZATION_ERROR_REF},
)
async def upload_direct(
    body: Annotated[
        UploadFileRequest,
        Body(description="Схема получения метаданных загружаемого медиа-файла."),
    ],
    file_service: FilesServiceDependency,
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
    body : UploadFileRequest
        Данные, полученные от клиента в теле запроса.
    file_service : FilesService
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
    file_id, presigned_url = await file_service.get_upload_presigned_url(
        body.content_type,
        body.title,
        body.description,
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
    responses={401: AUTHORIZATION_ERROR_REF},
)
async def upload_confirm(
    body: Annotated[
        ConfirmUploadRequest,
        Body(description="Схема получения UUID медиа-файла для подтверждения загрузки"),
    ],
    file_service: FilesServiceDependency,
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
    file_service : FilesService
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
    "/{file_id}/download/direct",
    response_model=PresignedURLResponse,
    status_code=status.HTTP_200_OK,
    summary="Получение Presigned URL для получения медиа-файлов из приватного хранилища.",
    response_description="URL для скачивания получена успешно",
    responses={401: AUTHORIZATION_ERROR_REF},
)
async def download_direct(
    file_id: Annotated[
        UUID,
        Path(description="UUID файла для скачивания на клиент."),
    ],
    file_service: FilesServiceDependency,
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
    file_service : FilesService
        Зависимость сервиса работы с файлами.
    payload : Payload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    PresignedURLResponse
        Успешный ответ о генерации presigned-url для скачивания.
    """
    file_id, presigned_url = await file_service.get_download_presigned_url(
        file_id,
        payload["sub"],
    )

    return PresignedURLResponse(
        file_id=file_id,
        presigned_url=presigned_url,
        detail="Presigned URL generated successfully.",
    )
