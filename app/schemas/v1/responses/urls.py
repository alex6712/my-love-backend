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


class PresignedURLsBatchResponse(StandardResponse):
    """Модель ответа сервера с вложенными Presigned URL.

    Используется в качестве ответа с сервера на запрос на загрузку
    или получение пакета медиа-файлов.

    Attributes
    ----------
    urls : list[PresignedURLDTO]
        Подписанные ссылки для каждого файла в пакете.
    """

    urls: list[PresignedURLDTO] = Field(
        description="Подписанные ссылки для каждого файла в пакете.",
    )
