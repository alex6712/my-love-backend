from uuid import UUID

from pydantic import BaseModel, Field

from app.core.types import UNSET, Maybe


class UploadFileRequest(BaseModel):
    """Схема запроса на получение presigned URL для загрузки файла.

    Attributes
    ----------
    client_ref_id : str
        Произвольный клиентский идентификатор для корреляции результата.
    content_type : str
        MIME-тип отправляемого файла.
    title : str
        Наименование медиа-файла.
    description : str | None
        Описание медиа-файла.
    """

    client_ref_id: str = Field(
        description="Произвольный клиентский идентификатор для корреляции результата.",
        examples=["file-upload-1"],
    )
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


class PatchFileRequest(BaseModel):
    """Схема запроса на частичное редактирование медиа-файла.

    Используется в качестве представления данных для частичного
    обновления полей файла. Все поля опциональны - передаются
    только те атрибуты, которые необходимо изменить.

    Attributes
    ----------
    title : Maybe[str]
        Наименование медиа файла. Если не передано - остаётся `UNSET`
        и текущее значение в базе данных не изменяется.
    description : Maybe[str | None]
        Описание медиа файла. Если не передано - остаётся `UNSET`
        и текущее значение не изменяется. Может быть явно передан
        как None для удаления описания.
    """

    title: Maybe[str] = Field(
        default_factory=lambda: UNSET,
        description="Наименование медиа файла",
        examples=["яскотятами"],
    )
    description: Maybe[str | None] = Field(
        default_factory=lambda: UNSET,
        description="Описание медиа файла",
        examples=["Файл смерти: кто прочитал, тот..."],
    )


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


class DownloadFilesBatchRequest(BaseModel):
    """Схема запроса на получение Presigned URLs скачивания пакета файлов.

    Attributes
    ----------
    files_uuids : list[UUID]
        Список UUID медиа-файлов для скачивания.
    """

    files_uuids: list[UUID] = Field(
        description="Список UUID медиа-файлов, которые необходимо скачать на клиент.",
        examples=[
            [
                "681cbf12-fe3f-41f4-92f1-c8cb33dfe47e",
                "f466bb69-bf31-4125-a29a-35166033e4ef",
            ]
        ],
    )
