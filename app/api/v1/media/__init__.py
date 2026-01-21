from fastapi import APIRouter

from app.api.v1.media.albums import router as _albums_router
from app.api.v1.media.files import router as _files_router

router = APIRouter(
    prefix="/media",
)

router.include_router(_files_router)
router.include_router(_albums_router)
