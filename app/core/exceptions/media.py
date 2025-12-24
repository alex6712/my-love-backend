from typing import Any

from app.core.exceptions.base import (
    BaseApplicationException,
    NotFoundException,
)


class MediaDomainException(BaseApplicationException):
    """Базовое исключение для ошибок, связанных с доменной логикой медиа.

    Parameters
    ----------
    *args : Any
        Стандартные аргументы исключения.
    detail : str | None
        Детальное сообщение об ошибке для пользователя или логирования.

    Notes
    -----
    Специализированное исключение для группировки всех ошибок,
    связанных с бизнес-логикой медиа домена.
    """

    def __init__(self, detail: str | None = None, *args: Any):
        super().__init__(detail, *args, domain="media")


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

    pass
