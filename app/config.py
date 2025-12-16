from functools import lru_cache
from os.path import abspath

from pydantic import EmailStr, field_validator
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


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore
