from pydantic import BaseModel, Field


class UploadFileRequest(BaseModel):
    """Схема запроса на получение Presigned URL загрузки файла.

    Attributes
    ----------
    content_type : str
        MIME-тип отправляемого файла.
    title : str
        Наименование медиа файла.
    description : str | None
        Описание медиа файла.
    """

    content_type: str = Field(
        description="MIME-тип отправляемого файла.",
        examples=["image/png"],
    )
    title: str = Field(
        description="Наименование медиа файла.",
        examples=["яскотятами"],
    )
    description: str | None = Field(
        description="Описание медиа файла.",
        examples=["Файл смерти: кто прочитал, тот..."],
    )
