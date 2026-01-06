from contextlib import asynccontextmanager
from typing import AsyncGenerator

import aioboto3  # type: ignore
from types_aiobotocore_s3 import S3Client

from app.config import Settings, get_settings

settings: Settings = get_settings()

_session: aioboto3.Session = aioboto3.Session(
    aws_access_key_id=settings.MINIO_ROOT_USER,
    aws_secret_access_key=settings.MINIO_ROOT_PASSWORD,
)
"""Project-wide сессия подключения к объектному хранилищу."""


@asynccontextmanager
async def get_s3_client() -> AsyncGenerator[S3Client, None]:
    """Асинхронный контекстный менеджер для получения S3 клиента.

    Используется для получения клиента объектного хранилища
    из пула подключений сессии приложения.

    Yields
    ------
    S3Client
        Асинхронный S3 клиент.
    """
    async with _session.client(  # type: ignore
        "s3",
        endpoint_url=f"http://{settings.MINIO_ENDPOINT}",
        config=aioboto3.session.AioConfig(  # type: ignore
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
    ) as client:  # type: ignore
        yield client
