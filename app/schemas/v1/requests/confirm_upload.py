from uuid import UUID

from pydantic import BaseModel, Field


class ConfirmUploadRequest(BaseModel):
    """Схема запроса на подтверждения завершения загрузки медиа-файла.

    Attributes
    ----------
    file_id : UUID
        UUID загруженного файла.
    """

    file_id: UUID = Field(
        description="UUID загруженного файла.",
        examples=["ccdc1e34-8772-4537-bdba-5e45c4be5d7c"],
    )
