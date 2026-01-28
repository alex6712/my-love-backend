from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header

from app.core.exceptions.base import (
    IdempotencyKeyNotPassedException,
    InvalidIdempotencyKeyFormatException,
)


async def get_idempotency_key(
    idempotency_key: UUID = Header(
        None,
        alias="Idempotency-Key",
        description="UUID ключ идемпотентности",
        example="24a8660f-d467-438c-b13d-5738fd30893d",
    ),
) -> UUID:
    """Зависимость, которая извлекает и проверяет заголовок Idempotency-Key.

    Проверяет заголовок `Idempotency-Key` на существование, извлекает
    из него значение ключа идемпотентности, валидирует его
    в качестве UUID v4.

    Parameters
    ----------
    request : Request
        Объект запроса, полученный через механизм FastAPI DI.

    Returns
    -------
    UUID
        Ключ идемпотентности из заголовка запроса.

    Raises
    ------
    IdempotencyKeyNotPassedException
        Если ключ не предоставлен в заголовке `Idempotency-Key`.
    InvalidIdempotencyKeyFormatException
        Если предоставленный ключ не в формате UUIDv4.
    """
    if not idempotency_key:
        raise IdempotencyKeyNotPassedException(
            detail="Idempotency key not found in the 'Idempotency-Key' header.",
        )

    if idempotency_key.version != 4:
        raise InvalidIdempotencyKeyFormatException(
            detail="Passed idempotency key is not UUIDv4.",
        )

    return idempotency_key


IdempotencyKeyDependency = Annotated[UUID, Depends(get_idempotency_key)]
"""Зависимость на получение ключа идемпотентности из заголовков запроса."""
