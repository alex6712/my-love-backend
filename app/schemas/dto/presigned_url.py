from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, Field


class PresignedURLDTO(BaseModel):
    """Модель представления подписанной ссылки.

    Attributes
    ----------
    file_id : UUID
        UUID загружаемого файла.
    presigned_url : str
        Presigned URL на загрузку или получение файла.
    """

    file_id: UUID = Field(
        description="UUID загружаемого файла.",
        examples=["ccdc1e34-8772-4537-bdba-5e45c4be5d7c"],
    )
    presigned_url: AnyHttpUrl = Field(
        description="Presigned URL на загрузку или получение файла.",
        examples=["https://amzn-s3-demo-bucket.s3.amazonaws.com"],
    )
