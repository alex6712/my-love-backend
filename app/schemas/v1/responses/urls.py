from pydantic import Field

from app.schemas.dto.file import DownloadFileErrorDTO, UploadFileErrorDTO
from app.schemas.dto.presigned_url import PresignedURLDTO, PresignedURLWithRefDTO
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


class PresignedURLsBatchResponse[S, F](StandardResponse):
    """Модель ответа сервера с presigned URLs для пакетной операции.

    Используется в качестве ответа на запрос загрузки или скачивания
    пакета медиа-файлов. Содержит как успешные результаты, так и ошибки
    по отдельным файлам, не прерывая обработку остального пакета.

    Parameters
    ----------
    S : type
        Тип элементов списка успешно обработанных файлов.
        Передаётся при параметризации: :class:`PresignedURLWithRefDTO`
        для загрузки, :class:`PresignedURLDTO` для скачивания.
    F : type
        Тип элементов списка ошибок.
        Передаётся при параметризации: :class:`UploadFileErrorDTO`
        для загрузки, :class:`DownloadFileErrorDTO` для скачивания.

    Attributes
    ----------
    successful : list[S]
        Presigned URLs для файлов, которые были успешно обработаны.
    failed : list[F]
        Ошибки для файлов, которые не удалось обработать.
        По умолчанию — пустой список.

    See Also
    --------
    PresignedURLsUploadBatchResponse : Параметризованный псевдоним для операции загрузки.
    PresignedURLsDownloadBatchResponse : Параметризованный псевдоним для операции скачивания.
    """

    successful: list[S] = Field(
        description="Подписанные ссылки для каждого файла в пакете.",
    )
    failed: list[F] = Field(description="Ошибки по файлам.")


type PresignedURLsUploadBatchResponse = PresignedURLsBatchResponse[
    PresignedURLWithRefDTO, UploadFileErrorDTO
]
"""Ответ сервера для операции пакетной загрузки файлов.

Параметризованный псевдоним :class:`PresignedURLsBatchResponse`,
где успешные результаты представлены как :class:`PresignedURLWithRefDTO`
(содержит ``client_ref_id`` для корреляции с исходным запросом),
а ошибки — как :class:`UploadFileErrorDTO`.
"""

type PresignedURLsDownloadBatchResponse = PresignedURLsBatchResponse[
    PresignedURLDTO, DownloadFileErrorDTO
]
"""Ответ сервера для операции пакетного скачивания файлов.

Параметризованный псевдоним :class:`PresignedURLsBatchResponse`,
где успешные результаты представлены как :class:`PresignedURLDTO`,
а ошибки — как :class:`DownloadFileErrorDTO`.
"""
