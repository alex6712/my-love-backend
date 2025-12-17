from typing import Annotated, Callable, TypeVar

from fastapi import Depends

from app.core.dependencies.database import UnitOfWorkDependency
from app.services.auth import AuthService
from app.services.interface import ServiceInterface

T = TypeVar("T", bound=ServiceInterface)

type ServiceDependencyCallable = Callable[[UnitOfWorkDependency], ServiceInterface]
"""Тип для вызываемого объекта зависимости сервисов"""


def get_service(service_type: type[T]) -> ServiceDependencyCallable:
    """Фабрика зависимостей для создания экземпляров сервисов.

    Создает и возвращает функцию-зависимость, которая инстанцирует
    сервис указанного типа, используя зависимость Unit of Work.

    Parameters
    ----------
    service_type : type[T]
        Класс сервиса для инстанцирования. Должен принимать в конструкторе
        экземпляр UnitOfWork в качестве единственного аргумента.

    Returns
    -------
    ServiceDependencyCallable
        Функция-зависимость, которая при вызове возвращает
        экземпляр указанного сервиса.
    """

    def dependency(unit_of_work: UnitOfWorkDependency) -> T:
        """Внутренняя функция-зависимость для создания сервиса.

        Создает экземпляр сервиса, используя переданный Unit of Work.

        Parameters
        ----------
        unit_of_work : UnitOfWorkDependency
            Зависимость Unit of Work, которая будет передана
            в конструктор сервиса.

        Returns
        -------
        T
            Экземпляр запрошенного сервиса с внедренной Unit of Work.
        """
        return service_type(unit_of_work)

    return dependency


AuthServiceDependency = Annotated[AuthService, Depends(get_service(AuthService))]
"""Зависимость на получение сервиса аутентификации и авторизации"""
