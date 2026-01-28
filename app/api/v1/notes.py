from typing import Annotated

from fastapi import APIRouter, Body, status

from app.core.dependencies.auth import StrictAuthenticationDependency
from app.core.dependencies.services import NotesServiceDependency
from app.core.docs import AUTHORIZATION_ERROR_REF
from app.schemas.v1.requests.create_notes import CreateNoteRequest
from app.schemas.v1.responses.standard import StandardResponse

router = APIRouter(
    prefix="/notes",
    tags=["notes"],
    responses={401: AUTHORIZATION_ERROR_REF},
)


@router.get(
    "",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Получение пользовательских заметок.",
    response_description="Список пользовательских заметок",
    include_in_schema=False,
)
async def get_notes(
    notes_service: NotesServiceDependency,
    payload: StrictAuthenticationDependency,
) -> StandardResponse:
    """TODO: Docstring"""
    return StandardResponse(detail="There are your notes.")


@router.post(
    "",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создание пользовательской заметки.",
    response_description="Заметка создана успешно",
    include_in_schema=False,
)
async def post_notes(
    body: Annotated[
        CreateNoteRequest, Body(description="Схема получения данных о заметке.")
    ],
    notes_service: NotesServiceDependency,
    payload: StrictAuthenticationDependency,
) -> StandardResponse:
    """TODO: Docstring"""
    notes_service.create_note(body.type, body.title, body.content, payload["sub"])

    return StandardResponse(detail="Note created successful.")
