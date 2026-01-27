from functools import lru_cache
from os.path import abspath

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ec import (
    EllipticCurvePrivateKey,
    EllipticCurvePublicKey,
)
from pydantic import (
    EmailStr,
    PostgresDsn,
    RedisDsn,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Класс конфигурации проекта.

    Использует `pydantic`_ + `python-dotenv`_ для загрузки настроек приложения из .env-файла.

    .. _`pydantic`:
        https://docs.pydantic.dev/
    .. _`python-dotenv`:
        https://pypi.org/project/python-dotenv/

    See Also
    --------
    pydantic
    python-dotenv

    Attributes
    ----------
    APP_NAME : str
        Название приложения.
    APP_VERSION : str
        Текущая версия приложения.
    APP_DESCRIPTION : str
        Полное описание приложения.
    APP_SUMMARY : str
        Краткое описание приложения.
    ADMIN_NAME : str
        Имя ответственного лица.
    ADMIN_EMAIL : EmailStr
        Email для связи с ответственным лицом.
    BACKEND_CORS_ORIGINS : List[str]
        Список источников для CORS Middleware.
    CURRENT_API_PATH : str
        URL текущей версии API.
    POSTGRES_USER : str
        Пользователь базы данных для подключения.
    POSTGRES_PASSWORD : str
        Пароль пользователя для подключения к базе данных.
    POSTGRES_PORT : int
        Порт базы данных.
    POSTGRES_DB : str
        Название базы данных.
    POSTGRES_DSN : PostgresDsn
        Строка подключения (ссылка) к базе данных.
    REDIS_HOST : str
        Хост Redis.
    REDIS_PASSWORD : str
        Пароль для подключения к Redis.
    REDIS_PORT : int
        Порт Redis.
    REDIS_DB : int
        Номер базы данных Redis.
    REDIS_URL : RedisDsn
        URL Redis.
    MINIO_HOST : str
        Наименование хоста, на котором размещён сервер MinIO.
    MINIO_ROOT_USER : str
        MinIO Access key (root пользователь).
    MINIO_ROOT_PASSWORD : str
        MinIO Secret key (пароль root пользователя).
    MINIO_BUCKET_NAME : str
        Наименование бакета на сервере MinIO.
    PRESIGNED_URL_EXPIRATION : int
        Базовое время жизни Presigned URL на загрузку файлов.
    PRIVATE_SIGNATURE_KEY_PASSWORD: str
        Пароль для дешифровки приватного ключа кодирования JWT.
    PRIVATE_SIGNATURE_KEY : EllipticCurvePrivateKey | None
        Приватный ключ подписи JWT.
    PUBLIC_SIGNATURE_KEY : EllipticCurvePublicKey | None
        Публичный ключ подписи JWT.
    JWT_ALGORITHM : str
        Алгоритм кодирования JWT.
    ACCESS_TOKEN_LIFETIME_MINUTES : int
        Время жизни access-токена в минутах.
    REFRESH_TOKEN_LIFETIME_DAYS : int
        Время жизни refresh-токена в днях.
    """

    APP_NAME: str
    APP_VERSION: str
    APP_DESCRIPTION: str
    APP_SUMMARY: str

    ADMIN_NAME: str
    ADMIN_EMAIL: EmailStr

    BACKEND_CORS_ORIGINS: list[str]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, value: list[str] | str) -> list[str]:
        if isinstance(value, str) and not value.startswith("["):
            return [i.strip() for i in value.split(",")]

        raise ValueError(value)

    CURRENT_API_PATH: str

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_PORT: int
    POSTGRES_DB: str

    POSTGRES_DSN: PostgresDsn

    REDIS_HOST: str
    REDIS_PASSWORD: str
    REDIS_PORT: int
    REDIS_DB: int

    REDIS_URL: RedisDsn

    MINIO_HOST: str
    MINIO_ROOT_USER: str
    MINIO_ROOT_PASSWORD: str
    MINIO_BUCKET_NAME: str

    PRESIGNED_URL_EXPIRATION: int

    PRIVATE_SIGNATURE_KEY_PASSWORD: str

    JWT_ALGORITHM: str
    ACCESS_TOKEN_LIFETIME_MINUTES: int
    REFRESH_TOKEN_LIFETIME_DAYS: int

    model_config = SettingsConfigDict(
        env_file=abspath(".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        enable_decoding=False,
        extra="ignore",
    )

    PRIVATE_SIGNATURE_KEY: EllipticCurvePrivateKey | None = None
    PUBLIC_SIGNATURE_KEY: EllipticCurvePublicKey | None = None

    @model_validator(mode="after")
    def load_keys(self) -> "Settings":
        """Загружает приватный и публичный ключи после инициализации модели"""
        public_key_path = abspath("keys/public_key.pem")

        with open(public_key_path, "rb") as key_file:
            self.PUBLIC_SIGNATURE_KEY = serialization.load_pem_public_key(  # type: ignore
                key_file.read()
            )

        if not self.PRIVATE_SIGNATURE_KEY_PASSWORD:
            raise ValueError(
                "PRIVATE_SIGNATURE_KEY_PASSWORD is required to load the private key"
            )

        private_key_path = abspath("keys/private_key.pem.enc")

        with open(private_key_path, "rb") as key_file:
            encrypted_key = key_file.read()
            try:
                private_key = serialization.load_pem_private_key(
                    encrypted_key,
                    password=self.PRIVATE_SIGNATURE_KEY_PASSWORD.encode("utf-8"),
                )
            except Exception as e:
                raise ValueError(f"Failed to decrypt private key: {e}")

            self.PRIVATE_SIGNATURE_KEY = private_key  # type: ignore

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore
