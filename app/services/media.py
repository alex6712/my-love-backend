from uuid import UUID

from app.infrastructure.postgresql import UnitOfWork
from app.repositories.media import MediaRepository
from app.schemas.dto.album import AlbumDTO


class MediaService:
    """TODO: документация"""

    def __init__(self, unit_of_work: UnitOfWork):
        super().__init__()

        self._media_repo: MediaRepository = unit_of_work.get_repository(MediaRepository)

    async def create_album(
        self,
        title: str,
        description: str | None,
        cover_url: str | None,
        is_private: bool,
        created_by: UUID,
    ) -> None:
        """TODO: документация"""
        await self._media_repo.add_album(
            title, description, cover_url, is_private, created_by
        )

    async def get_albums(self, creator_id: UUID) -> list[AlbumDTO]:
        """TODO: документация"""
        return await self._media_repo.get_albums_by_creator_id(creator_id)
