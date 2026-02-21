from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Path, Query, status

from app.core.dependencies.auth import StrictAuthenticationDependency
from app.core.dependencies.services import NoteServiceDependency
from app.core.docs import AUTHORIZATION_ERROR_REF
from app.core.enums import NoteType
from app.schemas.v1.requests.notes import CreateNoteRequest, PatchNoteRequest
from app.schemas.v1.responses.notes import NotesResponse
from app.schemas.v1.responses.standard import StandardResponse

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
    note_service: NoteServiceDependency,
    payload: StrictAuthenticationDependency,
    note_type: Annotated[
        NoteType | None, Query(alias="t", description="Тип заметок для получения.")
    ] = None,
    offset: Annotated[
        int,
        Query(
            ge=0,
            description="Смещение от начала списка (количество пропускаемых заметок).",
        ),
    ] = 0,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=50,
            description="Количество возвращаемых заметок.",
        ),
    ] = 10,
) -> NotesResponse:
    """Получение списка всех доступных пользователю заметок с пагинацией.

    Возвращает список заметок, доступных пользователю с UUID, переданным в токене доступа.
    Поддерживает пагинацию для работы с большими объемами данных.

    Parameters
    ----------
    note_service : NoteService
        Зависимость сервиса работы с пользовательскими заметками.
    payload : Payload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.
    note_type : NoteType | None
        Тип заметок для получения.
    offset : int, optional
        Смещение от начала списка (количество пропускаемых заметок).
    limit : int, optional
        Количество возвращаемых заметок.

    Returns
    -------
    NotesResponse
        Объект ответа, содержащий список доступных пользователю заметок
        в пределах заданной пагинации и общее количество найденных заметок.
    """
    notes, total = await note_service.get_notes(
        note_type, offset, limit, payload["sub"]
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
    note_service: NoteServiceDependency,
    payload: StrictAuthenticationDependency,
) -> StandardResponse:
    """Создание пользовательской заметки.

    Получает необходимую информацию для создание заметки и регистрирует
    её в системе.

    Parameters
    ----------
    body : CreateNoteRequest
        Схема получения данных о заметке.
    note_service : NoteService
        Зависимость сервиса работы с пользовательскими заметками.
    payload : Payload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    StandardResponse
        Успешный ответ о создании новой заметки.
    """
    note_service.create_note(body.type, body.title, body.content, payload["sub"])

    return StandardResponse(detail="New note created successful.")


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
    note_service: NoteServiceDependency,
    payload: StrictAuthenticationDependency,
) -> StandardResponse:
    """Частичное изменение пользовательской заметки.

    Проверяет права владения текущего пользователя над заметкой с
    переданным UUID, изменяет только переданные атрибуты при достатке прав.
    Все поля в теле запроса опциональны — передаются только те атрибуты,
    которые необходимо изменить.

    Parameters
    ----------
    note_id : UUID
        UUID заметки к изменению.
    body : PatchNoteRequest
        Схема частичного обновления данных о заметке.
        Содержит только те поля, которые нужно обновить.
    note_service : NoteService
        Зависимость сервиса работы с пользовательскими заметками.
    payload : Payload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    StandardResponse
        Успешный ответ о результате изменения заметки.
    """
    await note_service.update_note(note_id, body.title, body.content, payload["sub"])

    return StandardResponse(detail="Note content updated successful.")


@router.delete(
    "/{note_id}",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Удаление пользовательской заметки.",
    response_description="Заметка успешно изменено",
)
async def delete_notes(
    note_id: Annotated[UUID, Path(description="UUID изменяемой заметки.")],
    note_service: NoteServiceDependency,
    payload: StrictAuthenticationDependency,
) -> StandardResponse:
    """Удаление пользовательской заметки.

    Проверяет права владения текущего пользователя над заметкой с
    переданным UUID, Удаление её из системы при достатке прав.

    Parameters
    ----------
    note_id : UUID
        UUID заметки к удалению.
    note_service : NoteService
        Зависимость сервиса работы с пользовательскими заметками.
    payload : Payload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    StandardResponse
        Успешный ответ об удалении заметки.
    """
    await note_service.delete_note(note_id, payload["sub"])

    return StandardResponse(detail="Note deleted successful.")
