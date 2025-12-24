from typing import Any, Literal

from app.core.exceptions.base import BaseApplicationException
from app.core.security import TokenType

type CredentialsType = Literal["password", "token"]


class AuthDomainException(BaseApplicationException):
    """Базовое исключение для ошибок, связанных с доменной логикой аутентификации.

    Parameters
    ----------
    *args : Any
        Стандартные аргументы исключения.
    detail : str | None
        Детальное сообщение об ошибке для пользователя или логирования.

    Notes
    -----
    Специализированное исключение для группировки всех ошибок,
    связанных с бизнес-логикой домена аутентификации.
    """

    def __init__(self, detail: str | None = None, *args: Any):
        super().__init__(detail, *args, domain="auth")


class CredentialsException(AuthDomainException):
    """Исключение при ошибках аутентификации и проверки учетных данных.

    Parameters
    ----------
    *args : Any
        Стандартные аргументы исключения.
    detail : str
        Детальное сообщение об ошибке.
    credentials_type : CredentialsType
        Тип учетных данных, которые вызвали ошибку.

    Attributes
    ----------
    credentials_type : CredentialsType
        Тип учетных данных, связанных с исключением.

    Notes
    -----
    Различает ошибки аутентификации по паролю и по токену для
    последующей обработки и логирования.
    """

    def __init__(self, detail: str, *args: Any, credentials_type: CredentialsType):
        super().__init__(detail, *args)

        self.credentials_type: CredentialsType = credentials_type


class TokenNotPassedException(AuthDomainException):
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
    Используется для обработки случаев, когда в headers запроса
    отсутствует обязательный токен аутентификации или авторизации.
    """

    def __init__(self, detail: str, *args: Any, token_type: TokenType):
        super().__init__(detail, *args)

        self.token_type: TokenType = token_type


class TokenRevokedException(AuthDomainException):
    """Исключение при попытке использования отозванного токена.

    Notes
    -----
    Возникает в случае, когда токен, предоставленный в запросе, отозван.
    Это может произойти, например, при выходе пользователя из системы.
    """

    pass
