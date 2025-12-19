from typing import Any, Literal

from app.core.security import TokenType


class BaseApplicationException(Exception):
    """Базовое исключение для всех прикладных исключений приложения.

    Parameters
    ----------
    *args : Any
        Стандартные аргументы исключения.
    detail : str | None, optional
        Детальное сообщение об ошибке для пользователя или логирования.

    Notes
    -----
    Все прикладные исключения должны наследоваться от этого класса.
    Предоставляет единый интерфейс для передачи детализированных сообщений об ошибках.
    """

    def __init__(self, *args: Any, detail: str | None = None):
        super().__init__(detail, *args)


class UnitOfWorkContextClosedException(BaseApplicationException):
    """Исключение, вызываемое при попытке использования закрытого контекста Unit of Work.

    Notes
    -----
    Возникает при попытке выполнить операцию с базой данных после закрытия
    сессии или контекста работы с Unit of Work.
    """

    pass


class UserDomainException(BaseApplicationException):
    """Базовое исключение для ошибок, связанных с доменной логикой пользователей.

    Notes
    -----
    Специализированное исключение для группировки всех ошибок,
    связанных с бизнес-логикой пользовательского домена.
    """

    pass


class CredentialsException(UserDomainException):
    """Исключение при ошибках аутентификации и проверки учетных данных.

    Parameters
    ----------
    *args : Any
        Стандартные аргументы исключения.
    detail : str
        Детальное сообщение об ошибке.
    credentials_type : Literal["password", "token"]
        Тип учетных данных, которые вызвали ошибку.

    Attributes
    ----------
    credentials_type : Literal["password", "token"]
        Тип учетных данных, связанных с исключением.

    Notes
    -----
    Различает ошибки аутентификации по паролю и по токену для
    последующей обработки и логирования.
    """

    type _CredentialsType = Literal["password", "token"]

    def __init__(self, *args: Any, detail: str, credentials_type: _CredentialsType):
        super().__init__(detail, *args)
        self.credentials_type = credentials_type


class TokenNotPassedException(UserDomainException):
    """Исключение при отсутствии обязательного токена в запросе.

    Parameters
    ----------
    *args : Any
        Стандартные аргументы исключения.
    detail : str
        Детальное сообщение об ошибке.
    token_type : TokenType
        Тип отсутствующего токена.

    Attributes
    ----------
    token_type : TokenType
        Конкретный тип токена, который отсутствует в запросе.

    Notes
    -----
    Используется для обработки случаев, когда в cookies запроса
    отсутствует обязательный токен аутентификации или авторизации.
    """

    def __init__(self, *args: Any, detail: str, token_type: TokenType):
        super().__init__(detail, *args)
        self.token_type: TokenType = token_type


class TokenRevokedException(UserDomainException):
    """Исключение при попытке использования отозванного токена.

    Notes
    -----
    Возникает в случае, когда токен, предоставленный в запросе, отозван.
    Это может произойти, например, при выходе пользователя из системы.
    """

    pass


class UserNotFoundException(UserDomainException):
    """Исключение при отсутствии запрашиваемого пользователя.

    Notes
    -----
    Возникает при попытке доступа к несуществующему пользователю
    или когда пользователь не найден в базе данных по предоставленным критериям.
    """

    pass


class UsernameAlreadyExistsException(UserDomainException):
    """Исключение при попытке создать пользователя с существующим username.

    Notes
    -----
    Возникает при попытке регистрации нового пользователя по `username`,
    который уже существует в базе данных.
    """

    pass


class MediaDomainException(BaseApplicationException):
    """Базовое исключение для ошибок, связанных с доменной логикой медиа альбомов и файлов.

    Notes
    -----
    Специализированное исключение для группировки всех ошибок,
    связанных с бизнес-логикой медиа домена.
    """

    pass


class MediaNotFoundException(MediaDomainException):
    """Исключение при отсутствии запрашиваемого медиа.

    Notes
    -----
    Возникает при попытке доступа к несуществующему медиа
    или когда медиа не найдено в базе данных по предоставленным критериям.
    """

    pass
