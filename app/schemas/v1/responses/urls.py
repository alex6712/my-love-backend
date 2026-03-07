from pydantic import Field

from app.schemas.dto.presigned_url import PresignedURLDTO
from app.schemas.v1.responses.standard import StandardResponse


class PresignedURLResponse(StandardResponse):
    """Модель ответа сервера с вложенной Presigned URL.

    Используется в качестве ответа с сервера на запрос на загрузку
    или получение медиа-файла.

    Attributes
    ----------
    url : PresignedURLDTO
        Подписанная ссылка вместе с UUID файла.
    """

    url: PresignedURLDTO = Field(
        description="Подписанная ссылка вместе с UUID файла.",
    )


class PresignedURLsBatchResponse[T](StandardResponse):
    """Модель ответа сервера с presigned URLs для пакетной операции.

    Используется в качестве ответа на запрос загрузки или скачивания
    пакета медиа-файлов. Содержит как успешные результаты, так и ошибки
    по отдельным файлам, не прерывая обработку остального пакета.

    Attributes
    ----------
    successful : list[PresignedURLDTO]
        Presigned URLs для файлов, которые были успешно обработаны.
    failed : list[T]
        Ошибки для файлов, которые не удалось обработать.
        Тип элементов зависит от операции: :class:`UploadFileErrorDTO`
        для загрузки, :class:`DownloadFileErrorDTO` для скачивания.
    """

    successful: list[PresignedURLDTO] = Field(
        description="Подписанные ссылки для каждого файла в пакете.",
    )
    failed: list[T] = Field(default_factory=lambda: [], description="Ошибки по файлам.")
