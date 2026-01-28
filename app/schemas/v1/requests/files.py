from uuid import UUID

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


class UploadFilesBatchRequest(BaseModel):
    """Схема запроса на получение Presigned URL загрузки пакета файлов.

    Attributes
    ----------
    files_metadata : list[UploadFileRequest]
        Метаданные для каждого файла.
    """

    files_metadata: list[UploadFileRequest] = Field(
        description="Метаданные для каждого файла.",
        min_length=1,
        max_length=50,
    )


class UpdateFileRequest(UploadFileRequest):
    """Схема запроса на редактирование медиа-файла.

    Используется в качестве представления данных для обновления
    полей файла. Наследуется от `UploadFileRequest`, т.к. имеет
    те же поля, но отличается семантически.

    See Also
    --------
    app.schemas.v1.requests.files.UploadFileRequest
    """


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
