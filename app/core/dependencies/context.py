from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core.dependencies.auth import (
    ServiceManagerDependency,
    StrictAuthenticationDependency,
)


async def get_partner_id(
    services: ServiceManagerDependency,
    payload: StrictAuthenticationDependency,
) -> UUID | None:
    """Зависимость, которая возвращает partner_id для текущего пользователя.

    Извлекает идентификатор партнёра из кэша Redis или, при его отсутствии,
    из базы данных через CoupleService. Результат кэшируется.

    Parameters
    ----------
    services : ServiceManager
        Менеджер сервисов уровня запроса (request-scoped).

        Предоставляет доступ к бизнес-сервисам приложения
        (например, auth, user, note, file и др.) через единый
        контейнер зависимостей.
    payload : StrictAuthenticationDependency
        Payload текущего access token.

    Returns
    -------
    UUID | None
        Идентификатор партнёра, или None если пользователь не состоит в паре.
    """
    partner = await services.couple.get_partner(payload.sub)

    return partner.id if partner else None


PartnerIdDependency = Annotated[UUID | None, Depends(get_partner_id)]
"""Зависимость на получение идентификатора партнёра текущего пользователя."""
