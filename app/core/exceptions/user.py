from typing import Any

from app.core.exceptions.base import (
    AlreadyExistsException,
    BaseApplicationException,
    NotFoundException,
)


class UserDomainException(BaseApplicationException):
    """Базовое исключение для ошибок, связанных с доменной логикой пользователей.

    Parameters
    ----------
    *args : Any
        Стандартные аргументы исключения.
    detail : str | None
        Детальное сообщение об ошибке для пользователя или логирования.

    Notes
    -----
    Специализированное исключение для группировки всех ошибок,
    связанных с бизнес-логикой пользовательского домена.
    """

    def __init__(self, detail: str | None = None, *args: Any):
        super().__init__(detail, *args, domain="user")


class UserNotFoundException(UserDomainException, NotFoundException):
    """Исключение при отсутствии запрашиваемого пользователя.

    Notes
    -----
    Возникает при попытке доступа к несуществующему пользователю
    или когда пользователь не найден в базе данных по предоставленным критериям.
    """

    pass


class UsernameAlreadyExistsException(UserDomainException, AlreadyExistsException):
    """Исключение при попытке создать пользователя с существующим username.

    Notes
    -----
    Возникает при попытке регистрации нового пользователя по `username`,
    который уже существует в базе данных.
    """

    pass
