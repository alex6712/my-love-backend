from fastapi import APIRouter

from .auth import router as _auth_router
from .couples import router as _couples_router
from .media import router as _media_router
from .notes import router as _notes_router
from .root import router as _root_router
from .users import router as _users_router

api_v1_router: APIRouter = APIRouter(
    prefix="/v1",
)

api_v1_router.include_router(_auth_router)
api_v1_router.include_router(_couples_router)
api_v1_router.include_router(_media_router)
api_v1_router.include_router(_notes_router)
api_v1_router.include_router(_root_router)
api_v1_router.include_router(_users_router)
