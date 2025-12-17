from abc import ABC

from app.core.unit_of_work import UnitOfWork


class ServiceInterface(ABC):
    """Интерфейс сервиса.

    Реализация паттерна Сервис.

    Attributes
    ----------
    unit_of_work : UnitOfWork
        Объект асинхронного контекста транзакции.
    """

    def __init__(self, unit_of_work: UnitOfWork):
        self.unit_of_work: UnitOfWork = unit_of_work
