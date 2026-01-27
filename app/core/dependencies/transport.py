from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request

from app.core.exceptions.base import (
    IdempotencyKeyNotPassedException,
    InvalidIdempotencyKeyFormatException,
)


async def get_idempotency_key(request: Request) -> UUID:
    """Зависимость, которая извлекает и проверяет заголовок Idempotency-Key.

    Проверяет заголовок `Idempotency-Key` на существование, извлекает
    из него строковое значение ключа идемпотентности, валидирует его
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
    idempotency_key = request.headers.get("Idempotency-Key")

    if not idempotency_key:
        raise IdempotencyKeyNotPassedException(
            detail="Idempotency key not found in the 'Idempotency-Key' header.",
        )

    invalid_format = InvalidIdempotencyKeyFormatException(
        detail="Passed idempotency key is not UUIDv4.",
    )

    try:
        parsed_uuid = UUID(idempotency_key)
    except ValueError:
        raise invalid_format

    if parsed_uuid.version != 4:
        raise invalid_format

    return parsed_uuid


IdempotencyKeyDependency = Annotated[UUID, Depends(get_idempotency_key)]
"""Зависимость на получение ключа идемпотентности из заголовков запроса."""
