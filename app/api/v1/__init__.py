from fastapi import APIRouter

from app.api.v1.auth import router as _auth_router
from app.api.v1.couples import router as _couples_router
from app.api.v1.media import router as _media_router
from app.api.v1.notes import router as _notes_router
from app.api.v1.users import router as _users_router

api_v1_router = APIRouter(
    prefix="/v1",
)

api_v1_router.include_router(_auth_router)
api_v1_router.include_router(_couples_router)
api_v1_router.include_router(_media_router)
api_v1_router.include_router(_notes_router)
api_v1_router.include_router(_users_router)
