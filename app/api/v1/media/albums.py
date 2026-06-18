from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Path, Query, status

from app.core.consts import DEFAULT_LIMIT, DEFAULT_OFFSET, MAX_LIMIT, MAX_OFFSET
from app.core.dependencies.auth import StrictAuthenticationDependency
from app.core.dependencies.context import PartnerIdDependency
from app.core.dependencies.services import ServiceManagerDependency
from app.core.docs import AUTHORIZATION_ERROR_REF
from app.core.enums import SortOrder
from app.schemas.dto.album import (
    CreateAlbumDTO,
    PublicAlbumWithItemsDTO,
    UpdateAlbumDTO,
)
from app.schemas.v1.requests.albums import (
    AttachFilesRequest,
    CreateAlbumRequest,
    PatchAlbumRequest,
)
from app.schemas.v1.responses.albums import AlbumResponse, AlbumsResponse
from app.schemas.v1.responses.standard import StandardResponse

router = APIRouter(
    prefix="/albums", tags=["media-albums"], responses={401: AUTHORIZATION_ERROR_REF}
)


@router.get(
    "",
    response_model=AlbumsResponse,
    status_code=status.HTTP_200_OK,
    summary="Получение списка всех доступных пользователю медиаальбомов.",
    response_description="Список всех доступных альбомов",
)
async def get_albums(
    services: ServiceManagerDependency,
    payload: StrictAuthenticationDependency,
    partner_id: PartnerIdDependency,
    offset: Annotated[
        int,
        Query(
            ge=0,
            le=MAX_OFFSET,
            description="Смещение от начала списка (количество пропускаемых альбомов).",
        ),
    ] = DEFAULT_OFFSET,
    limit: Annotated[
        int, Query(ge=1, le=MAX_LIMIT, description="Количество возвращаемых альбомов.")
    ] = DEFAULT_LIMIT,
    order: Annotated[
        SortOrder, Query(description="Направление сортировки альбомов.")
    ] = SortOrder.ASC,
) -> AlbumsResponse:
    """Получение списка всех доступных пользователю медиаальбомов с пагинацией.

    Возвращает список медиаальбомов, доступных пользователю с UUID, переданным в токене доступа.
    Поддерживает пагинацию для работы с большими объемами данных.

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
    partner_id : UUID | None
        Идентификатор партнёра, или None если пользователь не состоит в паре.
    offset : int, optional
        Смещение от начала списка (количество пропускаемых альбомов).
    limit : int, optional
        Количество возвращаемых альбомов.
    order : SortOrder, optional
        Направление сортировки альбомов.

    Returns
    -------
    AlbumsResponse
        Объект ответа, содержащий список доступных пользователю медиаальбомов
        в пределах заданной пагинации и общее количество найденных альбомов.
    """
    albums, total = await services.album.get_albums(
        offset, limit, order, payload.sub, partner_id
    )

    return AlbumsResponse(
        albums=albums, total=total, detail=f"Found {total} album entries."
    )


@router.post(
    "",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новый медиаальбом.",
    response_description="Медиа-альбом создан успешно",
)
async def post_album(
    body: Annotated[
        CreateAlbumRequest, Body(description="Схема получения данных о медиаальбоме.")
    ],
    services: ServiceManagerDependency,
    payload: StrictAuthenticationDependency,
) -> StandardResponse:
    """Создание нового медиаальбома.

    Создаёт новую запись в базе данных, устанавливая переданные в теле
    запроса атрибуты.

    Parameters
    ----------
    body : CreateAlbumRequest
        Данные, полученные от клиента в теле запроса.
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
    StandardResponse
        Успешный ответ о создании нового альбома.
    """
    await services.album.create_album(
        CreateAlbumDTO.model_validate({**body.model_dump(), "created_by": payload.sub})
    )

    return StandardResponse(detail="New album created successfully.")


@router.get(
    "/search",
    response_model=AlbumsResponse,
    status_code=status.HTTP_200_OK,
    summary="Поиск альбомов по переданному тексту.",
    response_description="Список альбомов с похожим названием или описанием",
)
async def search_albums(
    search_query: Annotated[
        str,
        Query(alias="q", min_length=2, description="Поисковый запрос пользователя."),
    ],
    services: ServiceManagerDependency,
    payload: StrictAuthenticationDependency,
    partner_id: PartnerIdDependency,
    threshold: Annotated[
        float,
        Query(ge=0.0, le=1.0, description="Порог сходства для поиска по триграммам."),
    ] = 0.15,
    offset: Annotated[
        int,
        Query(
            ge=0,
            le=MAX_OFFSET,
            description="Смещение от начала списка (количество пропускаемых альбомов).",
        ),
    ] = DEFAULT_OFFSET,
    limit: Annotated[
        int, Query(ge=1, le=MAX_LIMIT, description="Количество возвращаемых альбомов.")
    ] = DEFAULT_LIMIT,
) -> AlbumsResponse:
    """Поиск альбомов по переданному тексту.

    Возвращает список медиаальбомов, доступных пользователю с UUID, переданным в токене доступа,
    в наименовании или описании которых был найден поисковый запрос.

    Поиск проводится не только по полному вхождению, но и по триграммам.

    Parameters
    ----------
    search_query : str
        Поисковый запрос пользователя.
    services : ServiceManager
        Менеджер сервисов уровня запроса (request-scoped).

        Предоставляет доступ к бизнес-сервисам приложения
        (например, auth, user, note, file и др.) через единый
        контейнер зависимостей.
    payload : AccessTokenPayload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.
    partner_id : UUID | None
        Идентификатор партнёра, или None если пользователь не состоит в паре.
    threshold : float, optional
        Порог сходства для поиска по триграммам.
    offset : int, optional
        Смещение от начала списка (количество пропускаемых альбомов).
    limit : int, optional
        Количество возвращаемых альбомов.

    Returns
    -------
    AlbumsResponse
        Объект ответа, содержащий список найденных альбомов.
    """
    albums, total = await services.album.search_albums(
        search_query, threshold, offset, limit, payload.sub, partner_id
    )

    return AlbumsResponse(
        albums=albums, total=total, detail=f"Found {total} album entries."
    )


@router.get(
    "/{album_id}",
    response_model=AlbumResponse,
    status_code=status.HTTP_200_OK,
    summary="Получение подробной информации о медиаальбоме.",
    response_description="Информация о медиаальбоме вместе с его элементами",
)
async def get_album(
    album_id: Annotated[UUID, Path(description="UUID запрашиваемого альбома.")],
    services: ServiceManagerDependency,
    payload: StrictAuthenticationDependency,
    partner_id: PartnerIdDependency,
    offset: Annotated[
        int,
        Query(
            ge=0,
            le=MAX_OFFSET,
            description="Смещение от начала списка (количество пропускаемых элементов).",
        ),
    ] = DEFAULT_OFFSET,
    limit: Annotated[
        int, Query(ge=1, le=MAX_LIMIT, description="Количество возвращаемых элементов.")
    ] = 20,
) -> AlbumResponse:
    """Получение подробной информации о медиаальбоме.

    Возвращает подробный DTO с полной информацией о конкретном
    медиаальбоме, чей UUID был передан.

    Если текущий пользователь не имеет доступа к этому альбому
    или альбом с переданным UUID не существует, будет
    возвращена ошибка.

    Parameters
    ----------
    album_id : UUID
        UUID запрашиваемого альбома.
    services : ServiceManager
        Менеджер сервисов уровня запроса (request-scoped).

        Предоставляет доступ к бизнес-сервисам приложения
        (например, auth, user, note, file и др.) через единый
        контейнер зависимостей.
    payload : AccessTokenPayload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.
    partner_id : UUID | None
        Идентификатор партнёра, или None если пользователь не состоит в паре.
    offset : int, optional
        Смещение от начала списка (количество пропускаемых элементов).
    limit : int, optional
        Количество возвращаемых элементов.

    Returns
    -------
    AlbumResponse
        Подробная информация о конкретном медиаальбоме.
    """
    album = await services.album.get_album(
        album_id, offset, limit, payload.sub, partner_id
    )

    return AlbumResponse(
        album=PublicAlbumWithItemsDTO.from_internal(album),
        detail=f"Found album with {album.total} files (showing {len(album.items)}).",
    )


@router.patch(
    "/{album_id}",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Частичное изменение атрибутов существующего медиаальбома.",
    response_description="Данные успешно изменены",
)
async def patch_album(
    album_id: Annotated[UUID, Path(description="UUID медиаальбома к изменению.")],
    body: Annotated[
        PatchAlbumRequest,
        Body(description="Схема частичного обновления атрибутов альбома"),
    ],
    services: ServiceManagerDependency,
    payload: StrictAuthenticationDependency,
    partner_id: PartnerIdDependency,
) -> StandardResponse:
    """Частичное изменение медиаальбома по его UUID.

    Проверяет права владения текущего пользователя над альбомом с
    переданным UUID, изменяет только переданные атрибуты при достатке прав.
    Все поля в теле запроса опциональны - передаются только те атрибуты,
    которые необходимо изменить.

    Parameters
    ----------
    album_id : UUID
        UUID альбома к изменению.
    body : PatchAlbumRequest
        Данные, полученные от клиента в теле запроса.
        Содержит только те поля, которые нужно обновить.
    services : ServiceManager
        Менеджер сервисов уровня запроса (request-scoped).

        Предоставляет доступ к бизнес-сервисам приложения
        (например, auth, user, note, file и др.) через единый
        контейнер зависимостей.
    payload : AccessTokenPayload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.
    partner_id : UUID | None
        Идентификатор партнёра, или None если пользователь не состоит в паре.

    Returns
    -------
    StandardResponse
        Ответ о результате изменения медиаальбома.
    """
    await services.album.update_album(
        album_id, UpdateAlbumDTO.from_request_schema(body), payload.sub, partner_id
    )

    return StandardResponse(detail="Album info edited successfully.")


@router.delete(
    "/{album_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удаление медиаальбома по его UUID.",
    response_description="Медиа-альбом удалён успешно",
)
async def delete_album(
    album_id: Annotated[UUID, Path(description="UUID медиаальбома к удалению.")],
    services: ServiceManagerDependency,
    payload: StrictAuthenticationDependency,
) -> None:
    """Удаление медиаальбома по его UUID.

    Проверяет права владения текущего пользователя над альбомом с
    переданным UUID, удаляет его при достатке прав.

    Parameters
    ----------
    album_id : UUID
        UUID альбома к удалению.
    services : ServiceManager
        Менеджер сервисов уровня запроса (request-scoped).

        Предоставляет доступ к бизнес-сервисам приложения
        (например, auth, user, note, file и др.) через единый
        контейнер зависимостей.
    payload : AccessTokenPayload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.
    """
    await services.album.delete_album(album_id, payload.sub)


@router.patch(
    "/{album_id}/attach",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Привязка медиафайлов к альбому.",
    response_description="Медиа-файлы добавлены в альбом",
)
async def attach(
    album_id: Annotated[
        UUID, Path(description="UUID альбома, в который добавляются файлы.")
    ],
    body: Annotated[
        AttachFilesRequest, Body(description="Список UUID медиафайлов к добавлению.")
    ],
    services: ServiceManagerDependency,
    payload: StrictAuthenticationDependency,
    partner_id: PartnerIdDependency,
) -> StandardResponse:
    """Привязка медиафайлов к медиаальбому.

    Получает в теле запроса список UUID медиафайлов, которые
    будут добавлены в медиаальбом.

    Parameters
    ----------
    album_id : UUID
        UUID альбома, к которому добавляются медиафайлы.
    body : AttachFilesRequest
        Список UUID медиафайлов к добавлению.
    services : ServiceManager
        Менеджер сервисов уровня запроса (request-scoped).

        Предоставляет доступ к бизнес-сервисам приложения
        (например, auth, user, note, file и др.) через единый
        контейнер зависимостей.
    payload : AccessTokenPayload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.
    partner_id : UUID | None
        Идентификатор партнёра, или None если пользователь не состоит в паре.

    Returns
    -------
    StandardResponse
        Ответ о результате добавления файлов к альбому.
    """
    await services.album.attach_files(
        album_id, body.files_uuids, payload.sub, partner_id
    )

    return StandardResponse(detail="Files successfully attached to album.")


@router.patch(
    "/{album_id}/detach",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Отвязка медиафайлов от альбома.",
    response_description="Медиа-файлы удалены из альбома",
)
async def detach(
    album_id: Annotated[
        UUID, Path(description="UUID альбома, из которого удаляются файлы.")
    ],
    body: Annotated[
        AttachFilesRequest, Body(description="Список UUID медиафайлов к удалению.")
    ],
    services: ServiceManagerDependency,
    payload: StrictAuthenticationDependency,
    partner_id: PartnerIdDependency,
) -> StandardResponse:
    """Отвязка медиафайлов от медиаальбома.

    Получает в теле запроса список UUID медиафайлов, которые
    будут удалены из медиаальбома.

    Parameters
    ----------
    album_id : UUID
        UUID альбома, из которого удаляются файлы.
    body : AttachFilesRequest
        Список UUID медиафайлов к удалению.
    services : ServiceManager
        Менеджер сервисов уровня запроса (request-scoped).

        Предоставляет доступ к бизнес-сервисам приложения
        (например, auth, user, note, file и др.) через единый
        контейнер зависимостей.
    payload : AccessTokenPayload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.
    partner_id : UUID | None
        Идентификатор партнёра, или None если пользователь не состоит в паре.

    Returns
    -------
    StandardResponse
        Ответ о результате удаления файлов из альбома.
    """
    await services.album.detach_files(
        album_id, body.files_uuids, payload.sub, partner_id
    )

    return StandardResponse(detail="Files successfully detached from album.")
