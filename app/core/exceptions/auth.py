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


class _CredentialsException(AuthDomainException):
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


class IncorrectUsernameOrPasswordException(_CredentialsException):
    """Исключение при ошибке обработки запроса логина пользователя.

    Parameters
    ----------
    *args : Any
        Стандартные аргументы исключения.
    detail : str
        Детальное сообщение об ошибке.

    Notes
    -----
    Используется для обработки случаев, когда не получилось
    аутентифицировать пользователя по предоставленным учётным данным.
    """

    def __init__(self, detail: str, *args: Any):
        super().__init__(detail, *args, credentials_type="password")


class _TokenException(_CredentialsException):
    """Базовое исключения для ошибок обработки JSON Web Tokens.

    Parameters
    ----------
    *args : Any
        Стандартные аргументы исключения.
    detail : str
        Детальное сообщение об ошибке.
    token_type : TokenType
        Тип JSON Web Token.

    Attributes
    ----------
    token_type : TokenType
        Конкретный тип токена.

    Notes
    -----
    Является наследуемым классом для всех исключений, связанных с
    JSON Web Tokens.
    """

    def __init__(self, detail: str, *args: Any, token_type: TokenType):
        super().__init__(detail, *args, credentials_type="token")

        self.token_type: TokenType = token_type


class TokenNotPassedException(_TokenException):
    """Исключение при отсутствии обязательного токена в запросе.

    Notes
    -----
    Используется для обработки случаев, когда в headers запроса
    отсутствует обязательный токен аутентификации или авторизации.
    """

    pass


class TokenRevokedException(AuthDomainException):
    """Исключение при попытке использования отозванного токена.

    Notes
    -----
    Возникает в случае, когда токен, предоставленный в запросе, отозван.
    Это может произойти, например, при выходе пользователя из системы.
    """

    pass


class InvalidTokenException(_TokenException):
    """Исключение при неверной подписи токена.

    Notes
    -----
    Возникает в случае, когда не получается удостовериться в подлинности
    подписи токена. Например:
    - Подпись неверна (токен выпущен не нами);
    - В payload отсутствуют обязательные claims.
    """

    pass


class TokenSignatureExpiredException(_TokenException):
    """Исключение при просроченной подписи токена.

    Notes
    -----
    Возникает в случае, когда подпись токена подлинна, однако просрочена.
    """

    pass
