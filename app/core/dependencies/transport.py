from typing import Annotated
from uuid import UUID

from fastapi import Depends, File, Form, Request, UploadFile

from app.core.exceptions.base import (
    IdempotencyKeyNotPassedException,
    InvalidIdempotencyKeyFormatException,
)


class UploadFileRequestForm:
    """Запрос на загрузку медиа файла.

    Не является pydantic-схемой в изначальном понимании.
    Представляет собой самописный класс с атрибутами,
    соответствующими полям формы загрузки файла.

    Используется такой подход, т.к. при загрузке
    файла необходим MIME-тип "multipart/form-data".

    Pydantic-схемы базово валидируют только "application/json",
    из-за чего невозможно создать единую схему запроса на
    загрузку файла из всех полей Body, используя pydantic.

    Parameters
    ----------
    file : UploadFile
        Загружаемый медиа файл.
    title : str | None
        Наименование медиа файла.
    description : str | None
        Описание медиа файла.

    Attributes
    ----------
    file : UploadFile
        Загружаемый медиа файл.
    title : str | None
        Наименование медиа файла.
    description : str | None
        Описание медиа файла.

    Examples
    --------
    ```
    from typing import Annotated

    from fastapi import Depends, FastAPI

    from app.schemas.v1.requests.upload_file import UploadFileRequest

    app = FastAPI()


    @app.post("/upload")
    def upload(form_data: Annotated[UploadFileRequest, Depends()]):
        data = {}

        data["file_data"] = form_data.file.file

        if form_data.title:
            data["title"] = form_data.title
        if form_data.description:
            data["description"] = form_data.description

        return data
    ```
    """

    def __init__(
        self,
        *,
        file: Annotated[
            UploadFile,
            File(description="Загружаемый медиа файл"),
        ],
        title: Annotated[
            str | None,
            Form(
                description="Наименование медиа файла",
                examples=["яскотятами"],
            ),
        ] = "Новый файл",
        description: Annotated[
            str | None,
            Form(
                description="Описание медиа файла",
                examples=["Файл смерти: кто прочитал, тот..."],
            ),
        ] = None,
    ):
        self.file = file
        self.title = title
        self.description = description


async def get_idempotency_key(request: Request) -> UUID:
    """Зависимость, которая извлекает и проверяет заголовок Idempotency-Key.

    Проверяет заголовок `Idempotency-Key` на существование, извлекает
    из него строковое значение ключа идемпотентности, валидирует его
    в качестве UUID v4.

    Parameters
    ----------
    request : Request
        Объект запроса, полученный через механизм FastAPI DI.

    Returns
    -------
    UUID
        Ключ идемпотентности из заголовка запроса.

    Raises
    ------
    IdempotencyKeyNotPassedException
        Если ключ не предоставлен в заголовке `Idempotency-Key`.
    InvalidIdempotencyKeyFormatException
        Если предоставленный ключ не в формате UUIDv4.
    """
    idempotency_key = request.headers.get("Idempotency-Key")

    if not idempotency_key:
        raise IdempotencyKeyNotPassedException(
            detail="Idempotency key not found in the 'Idempotency-Key' header.",
        )

    invalid_format = InvalidIdempotencyKeyFormatException(
        detail="Passed idempotency key is not UUIDv4.",
    )

    try:
        parsed_uuid = UUID(idempotency_key)
    except ValueError:
        raise invalid_format

    if parsed_uuid.version != 4:
        raise invalid_format

    return parsed_uuid


UploadFileDependency = Annotated[UploadFileRequestForm, Depends()]
"""Зависимость для формы загрузки медиа файла."""

IdempotencyKeyDependency = Annotated[UUID, Depends(get_idempotency_key)]
"""Зависимость на получение ключа идемпотентности из заголовков запроса."""
