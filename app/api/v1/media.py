from uuid import UUID

from fastapi import APIRouter, status

from app.core.dependencies.auth import StrictAuthenticationDependency
from app.schemas.v1.responses.standard import StandardResponse

router = APIRouter(
    prefix="/media",
    tags=["media"],
)


@router.get(
    "/albums",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Получение списка всех доступных пользователю медиа альбомов.",
)
async def get_albums(
    payload: StrictAuthenticationDependency,
) -> StandardResponse:
    """ """
    return StandardResponse(message="There are your albums!")


@router.post(
    "/albums",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новый медиа альбом.",
)
async def post_albums(
    payload: StrictAuthenticationDependency,
) -> StandardResponse:
    """ """
    return StandardResponse(
        code=status.HTTP_201_CREATED,
        message="New album created!",
    )


@router.delete(
    "/albums/{album_id}",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Удалить медиа альбом.",
)
async def delete_album(
    album_id: UUID,
    payload: StrictAuthenticationDependency,
) -> StandardResponse:
    """ """
    return StandardResponse(message="Oh no, you killed Kenny!")
