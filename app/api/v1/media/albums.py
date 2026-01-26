from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Path, Query, status

from app.core.dependencies.auth import StrictAuthenticationDependency
from app.core.dependencies.services import AlbumsServiceDependency
from app.core.docs import AUTHORIZATION_ERROR_REF
from app.schemas.v1.requests.attach_files import AttachFilesRequest
from app.schemas.v1.requests.create_album import CreateAlbumRequest
from app.schemas.v1.requests.update_album import UpdateAlbumRequest
from app.schemas.v1.responses.albums import AlbumResponse, AlbumsResponse
from app.schemas.v1.responses.standard import StandardResponse

router = APIRouter(
    prefix="/albums",
    tags=["media-albums"],
)


@router.get(
    "",
    response_model=AlbumsResponse,
    status_code=status.HTTP_200_OK,
    summary="Получение списка всех доступных пользователю медиа альбомов.",
    response_description="Список всех доступных альбомов",
    responses={401: AUTHORIZATION_ERROR_REF},
)
async def get_albums(
    albums_service: AlbumsServiceDependency,
    payload: StrictAuthenticationDependency,
    offset: Annotated[
        int,
        Query(
            ge=0,
            le=100,
            description="Смещение от начала списка (количество пропускаемых альбомов).",
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
    albums_service : AlbumsService
        Зависимость сервиса работы с альбомами.
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
    albums = await albums_service.get_albums(offset, limit, payload["sub"])

    return AlbumsResponse(albums=albums, detail=f"Found {len(albums)} album entries.")


@router.post(
    "",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новый медиа альбом.",
    response_description="Медиа-альбом создан успешно",
    responses={401: AUTHORIZATION_ERROR_REF},
)
async def post_albums(
    body: Annotated[
        CreateAlbumRequest, Body(description="Схема получения данных о медиа альбоме.")
    ],
    albums_service: AlbumsServiceDependency,
    payload: StrictAuthenticationDependency,
) -> StandardResponse:
    """Создание нового медиа альбома.

    Создаёт новую запись в базе данных, устанавливая переданные в теле
    запроса атрибуты.

    Parameters
    ----------
    body : CreateAlbumRequest
        Данные, полученные от клиента в теле запроса.
    albums_service : AlbumsServiceDependency
        Зависимость сервиса работы с альбомами.
    payload : Payload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    StandardResponse
        Успешный ответ о создании нового альбома.
    """
    albums_service.create_album(
        title=body.title,
        description=body.description,
        cover_url=body.cover_url,
        is_private=body.is_private,
        created_by=payload["sub"],
    )

    return StandardResponse(detail="New album created successfully.")


@router.get(
    "/search",
    response_model=AlbumsResponse,
    status_code=status.HTTP_200_OK,
    summary="Поиск альбомов по переданному тексту.",
    response_description="Список альбомов с похожим названием или описанием",
    responses={401: AUTHORIZATION_ERROR_REF},
)
async def search_albums(
    search_query: Annotated[
        str,
        Query(alias="q", min_length=2, description="Поисковый запрос пользователя."),
    ],
    albums_service: AlbumsServiceDependency,
    payload: StrictAuthenticationDependency,
    threshold: Annotated[
        float,
        Query(ge=0.0, le=1.0, description="Порог сходства для поиска по триграммам."),
    ] = 0.15,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=50,
            description="Количество возвращаемых альбомов.",
        ),
    ] = 10,
) -> AlbumsResponse:
    """Поиск альбомов по переданному тексту.

    Возвращает список медиа альбомов, доступных пользователю с UUID, переданным в токене доступа,
    в наименовании или описании которых был найден поисковый запрос.

    Поиск проводится не только по полному вхождению, но и по триграммам.

    Parameters
    ----------
    search_query : str
        Поисковый запрос пользователя.
    albums_service : AlbumsService
        Зависимость сервиса работы с альбомами.
    payload : Payload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.
    threshold : float, optional
        Порог сходства для поиска по триграммам.
    limit : int, optional
        Количество возвращаемых альбомов.

    Returns
    -------
    AlbumsResponse
        Объект ответа, содержащий список найденных альбомов.
    """
    albums = await albums_service.search_albums(
        search_query, threshold, limit, payload["sub"]
    )

    return AlbumsResponse(albums=albums, detail=f"Found {len(albums)} album entries.")


@router.get(
    "/{album_id}",
    response_model=AlbumResponse,
    status_code=status.HTTP_200_OK,
    summary="Получение подробной информации о медиа-альбоме.",
    response_description="Информация о медиа-альбоме вместе с его элементами",
    responses={401: AUTHORIZATION_ERROR_REF},
)
async def get_album(
    album_id: Annotated[UUID, Path(description="UUID запрашиваемого альбома.")],
    albums_service: AlbumsServiceDependency,
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
    album_id : UUID
        UUID запрашиваемого альбома.
    albums_service : AlbumsServiceDependency
        Зависимость сервиса работы с альбомами.
    payload : Payload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    AlbumResponse
        Подробная информация о конкретном медиа-альбоме.
    """
    album = await albums_service.get_album(album_id, payload["sub"])

    return AlbumResponse(
        album=album, detail=f"Found album with {len(album.items)} files."
    )


@router.put(
    "/{album_id}",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Изменение атрибутов существующего медиа-альбома.",
    response_description="Данные успешно изменены",
    responses={401: AUTHORIZATION_ERROR_REF},
)
async def put_album(
    album_id: Annotated[UUID, Path(description="UUID медиа альбома к изменению.")],
    body: Annotated[
        UpdateAlbumRequest,
        Body(description="Схема предоставления обновлённых атрибутов альбома"),
    ],
    albums_service: AlbumsServiceDependency,
    payload: StrictAuthenticationDependency,
) -> StandardResponse:
    """Изменение медиа альбома по его UUID.

    Проверяет права владения текущего пользователя над альбомом с
    переданным UUID, изменяет его атрибуты при достатке прав.

    Parameters
    ----------
    album_id : UUID
        UUID альбома к изменению.
    body : UpdateAlbumRequest
        Данные, полученные от клиента в теле запроса.
    albums_service : AlbumsServiceDependency
        Зависимость сервиса работы с альбомами.
    payload : Payload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    StandardResponse
        Ответ о результате изменения медиа альбома.
    """
    await albums_service.update_album(
        album_id,
        body.title,
        body.description,
        body.cover_url,
        body.is_private,
        payload["sub"],
    )

    return StandardResponse(detail="Album info edited successfully.")


@router.delete(
    "/{album_id}",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Удаление медиа альбома по его UUID.",
    response_description="Медиа-альбом удалён успешно",
    responses={401: AUTHORIZATION_ERROR_REF},
)
async def delete_album(
    album_id: Annotated[UUID, Path(description="UUID медиа альбома к удалению.")],
    albums_service: AlbumsServiceDependency,
    payload: StrictAuthenticationDependency,
) -> StandardResponse:
    """Удаление медиа альбома по его UUID.

    Проверяет права владения текущего пользователя над альбомом с
    переданным UUID, удаляет его при достатке прав.

    Parameters
    ----------
    album_id : UUID
        UUID альбома к удалению.
    albums_service : AlbumsServiceDependency
        Зависимость сервиса работы с альбомами.
    payload : Payload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    StandardResponse
        Ответ о результате удаления медиа альбома.
    """
    await albums_service.delete_album(album_id, payload["sub"])

    return StandardResponse(detail="Album entry deleted successfully.")


@router.patch(
    "/{album_id}/attach",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Привязка медиа-файлов к альбому.",
    response_description="Медиа-файлы добавлены в альбом",
    responses={401: AUTHORIZATION_ERROR_REF},
)
async def attach(
    album_id: Annotated[
        UUID, Path(description="UUID альбома, в который добавляются файлы.")
    ],
    body: Annotated[
        AttachFilesRequest, Body(description="Список UUID медиа файлов к добавлению.")
    ],
    albums_service: AlbumsServiceDependency,
    payload: StrictAuthenticationDependency,
) -> StandardResponse:
    """Привязка медиа-файлов к медиа-альбому.

    Получает в теле запроса список UUID медиа-файлов, которые
    будут добавлены в медиа альбом.

    Parameters
    ----------
    album_id : UUID
        UUID альбома, к которому добавляются медиа-файлы.
    body : AttachFilesRequest
        Список UUID медиа-файлов к добавлению.
    albums_service : AlbumsServiceDependency
        Зависимость сервиса работы с альбомами.
    payload : Payload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    StandardResponse
        Ответ о результате добавления файлов к альбому.
    """
    await albums_service.attach(album_id, body.files_uuids, payload["sub"])

    return StandardResponse(detail="Files successfully attached to album.")
