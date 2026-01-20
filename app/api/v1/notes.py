from fastapi import APIRouter, status

from app.core.dependencies.auth import StrictAuthenticationDependency
from app.core.docs import AUTHORIZATION_ERROR_EXAMPLES
from app.schemas.v1.responses.standard import StandardResponse

router = APIRouter(
    prefix="/notes",
    tags=["notes"],
)


@router.get(
    "/",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Получение пользовательских заметок.",
    response_description="Список пользовательских заметок",
    responses={401: AUTHORIZATION_ERROR_EXAMPLES},
)
async def get_notes(
    payload: StrictAuthenticationDependency,
) -> StandardResponse:
    """TODO: Docstring"""
    status.HTTP_401_UNAUTHORIZED
    return StandardResponse(detail="There are your notes.")


@router.post(
    "/",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создание пользовательской заметки.",
    response_description="Заметка создана успешно",
    responses={401: AUTHORIZATION_ERROR_EXAMPLES},
)
async def post_notes(
    payload: StrictAuthenticationDependency,
) -> StandardResponse:
    """TODO: Docstring"""
    return StandardResponse(detail="Note created successful.")
