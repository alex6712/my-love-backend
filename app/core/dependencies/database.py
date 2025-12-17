from typing import Annotated, Any, AsyncGenerator

from fastapi import Depends

from app.core.unit_of_work import UnitOfWork


async def get_unit_of_work() -> AsyncGenerator[UnitOfWork, Any]:
    """Создает уникальный объект асинхронного контекста транзакции.

    Используется для автоматической оркестрации репозиториями в сервисном слое:
    - по запросу конструирует требуемый репозиторий с внедрённой текущей сессией;
    - в автоматическом режиме выполняет `commit()` при успешной транзакции;
    - при любых исключениях выполняет `rollback()`,
      сохраняя таким образом атомарность операций с данными.

    Yields
    ------
    UnitOfWork
        Объект асинхронного контекста транзакции.
    """
    async with UnitOfWork() as uow:
        yield uow


UnitOfWorkDependency = Annotated[UnitOfWork, Depends(get_unit_of_work)]
"""Зависимость на получение экземпляра Unit of Work в асинхронном контексте"""
