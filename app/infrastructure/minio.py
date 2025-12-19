from minio import Minio

from app.config import Settings, get_settings

settings: Settings = get_settings()

minio_client: Minio = Minio(
    endpoint=settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ROOT_USER,
    secret_key=settings.MINIO_ROOT_PASSWORD,
    secure=False,
)
