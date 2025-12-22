from fastapi import APIRouter

from .auth import router as _auth_router
from .media import router as _albums_router
from .root import router as _root_router
from .users import router as _users_router

api_v1_router: APIRouter = APIRouter(
    prefix="/v1",
)

api_v1_router.include_router(_albums_router)
api_v1_router.include_router(_auth_router)
api_v1_router.include_router(_root_router)
api_v1_router.include_router(_users_router)
