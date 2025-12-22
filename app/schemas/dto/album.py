from datetime import datetime
from uuid import UUID

from app.schemas.dto.base import BaseDTO
from app.schemas.dto.user import CreatorDTO


class AlbumDTO(BaseDTO):
    """DTO для представления медиа альбома.

    Attributes
    ----------
    id : UUID
        Уникальный идентификатор медиа альбома.
    title : str
        Наименование альбома.
    description : str | None
        Описание альбома.
    cover_url : str | None
        URL обложки альбома.
    is_private : bool
        Видимость альбома (True - личный или False - публичный).
    creator : CreatorDTO
        DTO пользователя, создавшего альбом.
    created_at : datetime
        Временная метка создания альбома.
    """

    id: UUID
    title: str
    description: str | None
    cover_url: str | None
    is_private: bool

    creator: CreatorDTO

    created_at: datetime
