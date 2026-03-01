from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header


async def get_idempotency_key(
    idempotency_key: Annotated[
        UUID,
        Header(
            alias="Idempotency-Key",
            description="UUID ключ идемпотентности.",
            examples=["24a8660f-d467-438c-b13d-5738fd30893d"],
        ),
    ],
) -> UUID:
    """Зависимость, которая извлекает и проверяет заголовок Idempotency-Key.

    Проверяет заголовок `Idempotency-Key` на существование, извлекает
    из него значение ключа идемпотентности, валидирует его
    в качестве UUID.

    Parameters
    ----------
    request : Request
        Объект запроса, полученный через механизм FastAPI DI.

    Returns
    -------
    UUID
        Ключ идемпотентности из заголовка запроса.
    """
    return idempotency_key


IdempotencyKeyDependency = Annotated[UUID, Depends(get_idempotency_key)]
"""Зависимость на получение ключа идемпотентности из заголовков запроса."""
