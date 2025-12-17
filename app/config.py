from functools import lru_cache
from os.path import abspath

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey
from pydantic import EmailStr, field_validator, model_validator
from pydantic_settings import SettingsConfigDict, BaseSettings


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
    POSTGRES_USER : str
        Пользователь базы данных для подключения.
    POSTGRES_PASSWORD : str
        Пароль пользователя для подключения к базе данных.
    POSTGRES_PORT : int
        Порт базы данных.
    CURRENT_API_PATH : str
        URL текущей версии API.
    POSTGRES_DATABASE_NAME : str
        Название базы данных.
    POSTGRES_DSN : PostgresDsn
        Строка подключения (ссылка) к базе данных.
    PRIVATE_KEY_PASSWORD : str
        Пароль для дешифровки приватного ключа кодирования JWT.
    PRIVATE_KEY : RSAPrivateKey | None
        Приватный ключ шифрования JWT.
    PUBLIC_KEY : RSAPublicKey | None
        Публичный ключ шифрования JWT.
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
    POSTGRES_DATABASE_NAME: str

    POSTGRES_DSN: str

    PRIVATE_KEY_PASSWORD: str

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

    PRIVATE_KEY: RSAPrivateKey | None = None
    PUBLIC_KEY: RSAPublicKey | None = None

    @model_validator(mode="after")
    def load_keys(self) -> "Settings":
        """Загружает приватный и публичный ключи после инициализации модели"""
        public_key_path = abspath("keys/public_key.pem")

        with open(public_key_path, "rb") as key_file:
            self.PUBLIC_KEY = serialization.load_pem_public_key(key_file.read())  # type: ignore

        if not self.PRIVATE_KEY_PASSWORD:
            raise ValueError("PRIVATE_KEY_PASSWORD is required to load the private key")

        private_key_path = abspath("keys/private_key.pem.enc")

        with open(private_key_path, "rb") as key_file:
            encrypted_key = key_file.read()
            try:
                private_key = serialization.load_pem_private_key(
                    encrypted_key, password=self.PRIVATE_KEY_PASSWORD.encode("utf-8")
                )
            except Exception as e:
                raise ValueError(f"Failed to decrypt private key: {e}")

            self.PRIVATE_KEY = private_key  # type: ignore

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore
