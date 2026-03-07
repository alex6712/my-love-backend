from typing import Any

from app.core.exceptions.base import (
    BaseApplicationException,
    NotFoundException,
    UnexpectedStateException,
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

        self.media_type = media_type


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


class FileUploadPendingException(MediaDomainException):
    """Исключение при попытке скачать файл, загрузка которого ещё не завершена.

    Notes
    -----
    Возникает когда файл находится в статусе ``PENDING`` -
    загрузка в хранилище ещё не завершилась.
    Клиент может повторить запрос позже.
    """

    def __init__(self, detail: str | None = None, *args: Any):
        super().__init__("file", detail, *args)


class FileUploadFailedException(MediaDomainException):
    """Исключение при попытке скачать файл, загрузка которого завершилась ошибкой.

    Notes
    -----
    Возникает когда файл находится в статусе ``FAILED`` -
    загрузка в хранилище не была завершена из-за ошибки.
    Повторный запрос не имеет смысла без повторной загрузки файла.
    """

    def __init__(self, detail: str | None = None, *args: Any):
        super().__init__("file", detail, *args)


class FileDeletedException(MediaDomainException):
    """Исключение при попытке скачать удалённый файл.

    Notes
    -----
    Возникает когда файл находится в статусе ``DELETED``.
    В отличие от :class:`MediaNotFoundException`, файл существует в базе данных,
    но был явно удалён пользователем.
    """

    def __init__(self, detail: str | None = None, *args: Any):
        super().__init__("file", detail, *args)


class FileInvalidStatusException(MediaDomainException, UnexpectedStateException):
    """Исключение при обнаружении неизвестного статуса файла в базе данных.

    Notes
    -----
    Возникает когда статус файла, сохранённый в БД, не распознаётся
    бизнес-логикой операции скачивания. Сигнализирует о баге или рассинхроне
    схемы БД с кодом приложения.

    Не должно маппиться в пользовательскую ошибку - только логироваться
    и возвращаться клиенту как HTTP 500.
    """

    def __init__(self, detail: str | None = None, *args: Any):
        super().__init__("file", detail, *args)


class FilePresignedUrlGenerationFailedException(MediaDomainException):
    """Исключение при ошибке генерации presigned URL для скачивания файла.

    Notes
    -----
    Возникает когда S3-клиент не смог сгенерировать временную ссылку
    для доступа к файлу. Может сигнализировать о недоступности хранилища
    или некорректных параметрах запроса.

    Повторный запрос может помочь в случае временной недоступности хранилища.
    """

    def __init__(self, detail: str | None = None, *args: Any):
        super().__init__("file", detail, *args)
