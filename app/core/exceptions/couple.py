from typing import Any

from app.core.exceptions.base import (
    AlreadyExistsException,
    BaseApplicationException,
    NotFoundException,
)


class CoupleDomainException(BaseApplicationException):
    """Базовое исключение для ошибок, связанных с доменной логикой пар.

    Parameters
    ----------
    *args : Any
        Стандартные аргументы исключения.
    detail : str | None
        Детальное сообщение об ошибке для пользователя или логирования.

    Notes
    -----
    Специализированное исключение для группировки всех ошибок,
    связанных с бизнес-логикой домена пар.
    """

    def __init__(self, detail: str | None = None, *args: Any):
        super().__init__(detail, *args, domain="couple")


class CoupleNotFoundException(CoupleDomainException, NotFoundException):
    """Исключение при отсутствии запрашиваемой пары между пользователями.

    Notes
    -----
    Если при попытке получения пары пользователей по UUID партнёра
    не было найдено ни одной записи, то будет вызвано это исключение.
    """

    pass


class CoupleRequestNotFoundException(CoupleDomainException, NotFoundException):
    """Исключение при отсутствии запроса на создание пары.

    Notes
    -----
    Если при попытке получения запроса на создание пары пользователей не было
    найдено ни одной записи, то будет вызвано это исключение.
    """

    pass


class CoupleAlreadyExistsException(CoupleDomainException, AlreadyExistsException):
    """Исключение при попытке создать уже существующую пару пользователей.

    Notes
    -----
    Если при попытке регистрации новой пары пользователей по их UUID
    в базе данных уже существует зарегистрированная пара пользователей
    с такими же UUID, то будет выброшено это исключение.
    """

    pass


class CoupleRequestAlreadyExistsException(
    CoupleDomainException, AlreadyExistsException
):
    """Исключение при попытке отправить уже существующий запрос на создание пары.

    Notes
    -----
    Если при попытке регистрации новой пары пользователей по их UUID
    в базе данных уже существует запрос на создание пары пользователей
    с такими же UUID, то будет выброшено это исключение.
    """

    pass


class CoupleNotSelfException(CoupleDomainException):
    """Нельзя образовать пару с самим собой.

    Notes
    -----
    Если при попытке регистрации новой пары пользователей,
    клиент передал два одинаковых UUID.
    """

    pass
