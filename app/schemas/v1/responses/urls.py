from pydantic import Field

from .standard import StandardResponse


class PresignedURLResponse(StandardResponse):
    """Модель ответа сервера с вложенной Presigned URL.

    Используется в качестве ответа с сервера на запрос на загрузку
    или получение медиа-файла.

    Attributes
    ----------
    presigned_url : str
        Presigned URL на загрузку или получение файла.
    """

    presigned_url: str = Field(
        description="Presigned URL на загрузку или получение файла.",
        examples=["https://amzn-s3-demo-bucket.s3.amazonaws.com"],
    )
