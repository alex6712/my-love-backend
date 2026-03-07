from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel


class PresignedURLDTO(BaseModel):
    """Модель представления подписанной ссылки.

    Attributes
    ----------
    file_id : UUID
        UUID загружаемого файла.
    presigned_url : str
        Presigned URL на загрузку или получение файла.
    """

    file_id: UUID
    presigned_url: AnyHttpUrl


class PresignedURLWithRefDTO(PresignedURLDTO):
    """Модель представления подписанной ссылки с обратным `ref`.

    Используется для представления подписанной ссылки
    при запросе на загрузку файла на сервер.
    Содержит `client_ref_id` для корреляции.

    Attributes
    ----------
    client_ref_id: str
        Произвольный клиентский идентификатор для корреляции результата.
    """

    client_ref_id: str
