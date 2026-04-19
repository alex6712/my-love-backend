from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Path, Query, status

from app.core.consts import DEFAULT_LIMIT, DEFAULT_OFFSET, MAX_LIMIT, MAX_OFFSET
from app.core.dependencies.auth import StrictAuthenticationDependency
from app.core.dependencies.context import PartnerIdDependency
from app.core.dependencies.services import ServiceManagerDependency
from app.core.docs import AUTHORIZATION_ERROR_REF
from app.core.enums import NoteType, SortOrder
from app.schemas.dto.note import CreateNoteDTO, UpdateNoteDTO
from app.schemas.v1.requests.notes import CreateNoteRequest, PatchNoteRequest
from app.schemas.v1.responses.notes import NotesResponse
from app.schemas.v1.responses.standard import CountResponse, StandardResponse

router = APIRouter(
    prefix="/notes",
    tags=["notes"],
    responses={401: AUTHORIZATION_ERROR_REF},
)


@router.get(
    "",
    response_model=NotesResponse,
    status_code=status.HTTP_200_OK,
    summary="Получение пользовательских заметок.",
    response_description="Список пользовательских заметок",
)
async def get_notes(
    services: ServiceManagerDependency,
    payload: StrictAuthenticationDependency,
    partner_id: PartnerIdDependency,
    note_type: Annotated[
        NoteType | None, Query(alias="t", description="Тип заметок для получения.")
    ] = None,
    offset: Annotated[
        int,
        Query(
            ge=0,
            le=MAX_OFFSET,
            description="Смещение от начала списка (количество пропускаемых заметок).",
        ),
    ] = DEFAULT_OFFSET,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=MAX_LIMIT,
            description="Количество возвращаемых заметок.",
        ),
    ] = DEFAULT_LIMIT,
    order: Annotated[
        SortOrder,
        Query(
            description="Направление сортировки заметок.",
        ),
    ] = SortOrder.ASC,
) -> NotesResponse:
    """Получение списка всех доступных пользователю заметок с пагинацией.

    Возвращает список заметок, доступных пользователю с UUID, переданным в токене доступа.
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
    note_type : NoteType | None
        Тип заметок для получения.
    offset : int, optional
        Смещение от начала списка (количество пропускаемых заметок).
    limit : int, optional
        Количество возвращаемых заметок.
    order : SortOrder, optional
        Направление сортировки заметок.

    Returns
    -------
    NotesResponse
        Объект ответа, содержащий список доступных пользователю заметок
        в пределах заданной пагинации и общее количество найденных заметок.
    """
    notes, total = await services.note.get_notes(
        note_type, offset, limit, order, payload.sub, partner_id
    )

    return NotesResponse(
        notes=notes, total=total, detail=f"Found {total} note entries."
    )


@router.post(
    "",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создание пользовательской заметки.",
    response_description="Заметка создана успешно",
)
async def post_notes(
    body: Annotated[
        CreateNoteRequest, Body(description="Схема получения данных о заметке.")
    ],
    services: ServiceManagerDependency,
    payload: StrictAuthenticationDependency,
) -> StandardResponse:
    """Создание пользовательской заметки.

    Получает необходимую информацию для создание заметки и регистрирует
    её в системе.

    Parameters
    ----------
    body : CreateNoteRequest
        Схема получения данных о заметке.
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
        Успешный ответ о создании новой заметки.
    """
    await services.note.create_note(
        CreateNoteDTO.from_request_schema(body), payload.sub
    )

    return StandardResponse(detail="New note created successfully.")


@router.get(
    "/count",
    response_model=CountResponse,
    status_code=status.HTTP_200_OK,
    summary="Получение количества всех доступных пользователю заметок.",
    response_description="Количество доступных пользователю заметок.",
)
async def count(
    services: ServiceManagerDependency,
    payload: StrictAuthenticationDependency,
    partner_id: PartnerIdDependency,
) -> CountResponse:
    """Получение количества всех доступных пользователю заметок.

    Возвращает общее количество заметок, доступных пользователю
    с UUID, переданным в токене доступа, включая файлы его партнёра.

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

    Returns
    -------
    CountResponse
        Объект ответа, содержащий общее количество доступных
        пользователю заметок.
    """
    count = await services.note.count_notes(payload.sub, partner_id)

    return CountResponse(count=count, detail=f"Found {count} note entries.")


@router.patch(
    "/{note_id}",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Частичное изменение пользовательской заметки.",
    response_description="Заметка успешно изменено",
)
async def patch_notes(
    note_id: Annotated[UUID, Path(description="UUID изменяемой заметки.")],
    body: Annotated[
        PatchNoteRequest, Body(description="Схема частичного обновления заметки.")
    ],
    services: ServiceManagerDependency,
    payload: StrictAuthenticationDependency,
    partner_id: PartnerIdDependency,
) -> StandardResponse:
    """Частичное изменение пользовательской заметки.

    Проверяет права владения текущего пользователя над заметкой с
    переданным UUID, изменяет только переданные атрибуты при достатке прав.
    Все поля в теле запроса опциональны - передаются только те атрибуты,
    которые необходимо изменить.

    Parameters
    ----------
    note_id : UUID
        UUID заметки к изменению.
    body : PatchNoteRequest
        Схема частичного обновления данных о заметке.
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
        Успешный ответ о результате изменения заметки.
    """
    await services.note.update_note(
        note_id,
        UpdateNoteDTO.from_request_schema(body),
        payload.sub,
        partner_id,
    )

    return StandardResponse(detail="Note content updated successfully.")


@router.delete(
    "/{note_id}",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Удаление пользовательской заметки.",
    response_description="Заметка успешно изменено",
)
async def delete_notes(
    note_id: Annotated[UUID, Path(description="UUID изменяемой заметки.")],
    services: ServiceManagerDependency,
    payload: StrictAuthenticationDependency,
) -> StandardResponse:
    """Удаление пользовательской заметки.

    Проверяет права владения текущего пользователя над заметкой с
    переданным UUID, Удаление её из системы при достатке прав.

    Parameters
    ----------
    note_id : UUID
        UUID заметки к удалению.
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
        Успешный ответ об удалении заметки.
    """
    await services.note.delete_note(note_id, payload.sub)

    return StandardResponse(detail="Note deleted successfully.")
