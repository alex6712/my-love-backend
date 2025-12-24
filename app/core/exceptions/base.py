from typing import Any, Literal

type Domain = Literal["application", "auth", "user", "couple", "media"]


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

    Notes
    -----
    Возникает при попытке выполнить операцию с базой данных после закрытия
    сессии или контекста работы с Unit of Work.
    """

    pass


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
