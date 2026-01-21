from typing import Any

from app.core.types import Domain


class BaseApplicationException(Exception):
    """Базовое исключение для всех прикладных исключений приложения.

    Parameters
    ----------
    *args : Any
        Стандартные аргументы исключения.
    detail : str | None
        Детальное сообщение об ошибке для пользователя или логирования.
    domain : Domain
        Обозначение домена, в котором наследуемое исключение используется.

    Attributes
    ----------
    domain : Domain
        Обозначение домена, в котором наследуемое исключение используется.

    Notes
    -----
    Все прикладные исключения должны наследоваться от этого класса.
    Предоставляет единый интерфейс для передачи детализированных сообщений об ошибках.
    """

    def __init__(self, detail: str | None = None, *args: Any, domain: Domain):
        super().__init__(detail, *args)

        self.domain: Domain = domain

    @property
    def detail(self) -> str:
        return super().__str__()


class UnitOfWorkContextClosedException(BaseApplicationException):
    """Исключение, вызываемое при попытке использования закрытого контекста Unit of Work.

    Parameters
    ----------
    detail : str | None
        Детальное сообщение об ошибке для пользователя или логирования.
    *args : Any
        Стандартные аргументы исключения.

    Notes
    -----
    Возникает при попытке выполнить операцию с базой данных после закрытия
    сессии или контекста работы с Unit of Work.
    """

    def __init__(self, detail: str | None = None, *args: Any):
        super().__init__(detail, *args, domain="application")


class NotFoundException(BaseApplicationException):
    """Базовое исключение для группировки всех исключений типа `NotFound`.

    Notes
    -----
    Все исключения, связанные с логикой разных обработки `NotFound`
    различных доменов должны наследоваться от этого исключения.
    """

    pass


class AlreadyExistsException(BaseApplicationException):
    """Базовое исключение для группировки всех исключений типа `AlreadyExists`.

    Notes
    -----
    Все исключения, связанные с логикой разных обработки `AlreadyExists`
    различных доменов должны наследоваться от этого исключения.
    """

    pass


class IdempotencyKeyNotPassedException(BaseApplicationException):
    """Исключение, вызываемое при отсутствии ключа идемпотентности в заголовках запроса.

    Parameters
    ----------
    detail : str | None
        Детальное сообщение об ошибке для пользователя или логирования.
    *args : Any
        Стандартные аргументы исключения.

    Notes
    -----
    Возникает в случае, когда клиент отправил запрос на специфический эндпоинт,
    требующий ключ идемпотентности, однако не предоставил заголовок
    `Idempotency-Key`.
    """

    def __init__(self, detail: str | None = None, *args: Any):
        super().__init__(detail, *args, domain="application")


class InvalidIdempotencyKeyFormatException(BaseApplicationException):
    """Исключение, вызываемое при неверном типе ключа идемпотентности.

    Parameters
    ----------
    detail : str | None
        Детальное сообщение об ошибке для пользователя или логирования.
    *args : Any
        Стандартные аргументы исключения.

    Notes
    -----
    Возникает в случае, когда клиент отправил запрос на специфический эндпоинт,
    требующий ключ идемпотентности, однако предоставил ключ неверного формата.
    """

    def __init__(self, detail: str | None = None, *args: Any):
        super().__init__(detail, *args, domain="application")


class IdempotencyException(BaseApplicationException):
    """Исключение, вызываемое при конфликте обработки ключа идемпотентности.

    Возникает в случаях, когда запрос с переданным ключом идемпотентности
    уже обрабатывается или обнаружена другая ошибка, связанная с логикой
    идемпотентности.

    Parameters
    ----------
    detail : str | None
        Детальное сообщение об ошибке для пользователя или логирования.
    *args : Any
        Стандартные аргументы исключения.

    Notes
    -----
    Типичные сценарии использования:
    - Повторный запрос с ключом идемпотентности, который уже обрабатывается;
    - Неконсистентное состояние ключа идемпотентности в хранилище.
    """

    def __init__(self, detail: str | None = None, *args: Any):
        super().__init__(detail, *args, domain="application")
