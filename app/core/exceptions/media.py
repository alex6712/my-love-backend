from typing import Any

from app.core.exceptions.base import (
    BaseApplicationException,
    NotFoundException,
)
from app.core.types import MediaType


class MediaDomainException(BaseApplicationException):
    """Базовое исключение для ошибок, связанных с доменной логикой медиа.

    Parameters
    ----------
    *args : Any
        Стандартные аргументы исключения.
    media_type : Literal["album", "file"]
        Тип медиа.
    detail : str | None
        Детальное сообщение об ошибке для пользователя или логирования.

    Notes
    -----
    Специализированное исключение для группировки всех ошибок,
    связанных с бизнес-логикой медиа домена.
    """

    def __init__(self, media_type: MediaType, detail: str | None = None, *args: Any):
        super().__init__(detail, *args, domain="media")

        self.media_type: MediaType = media_type


class MediaNotFoundException(MediaDomainException, NotFoundException):
    """Исключение при отсутствии запрашиваемого медиа.

    Notes
    -----
    Возникает при попытке доступа к несуществующему медиа
    или когда медиа не найдено в базе данных по предоставленным критериям.
    """

    pass


class UnsupportedFileTypeException(MediaDomainException):
    """Исключение при попытке загрузить на сервер файл недопустимого формата.

    Notes
    -----
    Возникает при попытке загрузить на сервер файл с `content_type` не входящим
    в `["image/jpeg", "image/png", "video/mp4", "video/quicktime"]`.
    """

    def __init__(self, detail: str | None = None, *args: Any):
        super().__init__("file", detail, *args)


class UploadNotCompletedException(MediaDomainException):
    """Исключение при попытке подтвердить загрузку файла при отсутствии самого файла.

    Notes
    -----
    Возникает при попытке клиента подтвердить загрузку файла, однако
    при проверке оказывается, что предоставленный файл не существует
    в объектном хранилище.
    """

    def __init__(self, detail: str | None = None, *args: Any):
        super().__init__("file", detail, *args)
