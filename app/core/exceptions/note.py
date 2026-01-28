from typing import Any

from app.core.exceptions.base import (
    BaseApplicationException,
    NotFoundException,
)


class NoteDomainException(BaseApplicationException):
    """Базовое исключение для ошибок, связанных с доменной логикой заметок.

    Parameters
    ----------
    *args : Any
        Стандартные аргументы исключения.
    detail : str | None
        Детальное сообщение об ошибке для пользователя или логирования.

    Notes
    -----
    Специализированное исключение для группировки всех ошибок,
    связанных с бизнес-логикой домена заметок.
    """

    def __init__(self, detail: str | None = None, *args: Any):
        super().__init__(detail, *args, domain="note")


class NoteNotFoundException(NoteDomainException, NotFoundException):
    """Исключение при отсутствии запрашиваемой заметки.

    Notes
    -----
    Возникает при попытке доступа к несуществующей заметке
    или когда заметка не найдена в базе данных по предоставленным критериям.
    """

    pass
