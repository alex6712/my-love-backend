from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

from botocore.exceptions import ClientError
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import (
    get_openapi,
    validation_error_definition,  # type: ignore
)

from app.api.root import api_root_router
from app.api.v1 import api_v1_router
from app.config import get_settings
from app.core.docs import (
    AUTHORIZATION_ERROR_SCHEMA,
    CHANGE_PASSWORD_ERROR_SCHEMA,
    CHANGE_PASSWORD_VALIDATION_ERROR_SCHEMA,
    IDEMPOTENCY_CONFLICT_ERROR_SCHEMA,
    LOGIN_ERROR_SCHEMA,
    RATE_LIMIT_ERROR_SCHEMA,
    REGISTER_ERROR_SCHEMA,
)
from app.core.rate_limiter import limiter
from app.handlers import register_all_handlers
from app.infrastructure.postgresql import async_postgresql_engine
from app.infrastructure.redis import redis_client
from app.infrastructure.s3 import get_s3_client
from app.schemas.v1.responses.validation_error import ValidationErrorResponse

settings = get_settings()

tags_metadata = [
    {
        "name": "root",
        "description": "Получение информации о **приложении**.",
    },
    {
        "name": "authorization",
        "description": "Операции **регистрации** и **аутентификации**.",
    },
    {
        "name": "couples",
        "description": "Операции с **парами** между пользователями приложения.",
    },
    {
        "name": "users",
        "description": "Операции с **пользователями** приложения.",
    },
    {
        "name": "media-files",
        "description": "Операции с **медиа-файлами**: загрузка, скачивание, presigned URLs.",
    },
    {
        "name": "media-albums",
        "description": "Операции с **медиа-альбомами**: создание, получение, привязка файлов.",
    },
    {
        "name": "notes",
        "description": "Операции с пользовательскими **заметками**.",
    },
    {
        "name": "dashboard",
        "description": "Операции по получению агрегированных данных для **главной страницы** приложения.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, Any]:
    """Менеджер срока службы FastAPI-приложения.

    Используется для менеджмента самого приложения в процессе
    его работы.

    В данном случае выполняет следующие действия:
    - Инициализирует бакет MinIO через клиент `aioboto3`;
    - Создаёт пул подключений к Redis.

    Parameters
    ----------
    app : FastAPI
        Объект приложения для менеджмента.

    Yields
    ------
    None
        При успешном выполнении ничего не возвращает.
    """
    app.state.startup_at = datetime.now(timezone.utc)
    app.state.limiter = limiter

    async with get_s3_client() as s3_client:
        try:
            await s3_client.head_bucket(Bucket=settings.MINIO_BUCKET_NAME)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")

            if error_code in ("404", "NoSuchBucket"):
                await s3_client.create_bucket(Bucket=settings.MINIO_BUCKET_NAME)
            else:
                raise

    await redis_client.connect()

    yield

    await async_postgresql_engine.dispose()
    await redis_client.disconnect()


my_love_backend = FastAPI(
    title=settings.APP_NAME,
    summary=settings.APP_SUMMARY,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    openapi_tags=tags_metadata,
    lifespan=lifespan,
    contact={
        "name": settings.ADMIN_NAME,
        "email": settings.ADMIN_EMAIL,
    },
)

my_love_backend.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

my_love_backend.include_router(api_root_router)
my_love_backend.include_router(api_v1_router)

register_all_handlers()  # должен вызываться только после инициализации FastAPI приложения


def custom_openapi() -> dict[str, Any]:
    """Генерирует и возвращает кастомную схему OpenAPI для FastAPI приложения.

    Функция реализует паттерн кэширования (singleton-like) для схемы OpenAPI.
    При первом вызове генерирует полную схему на основе конфигурации приложения,
    добавляет кастомные компоненты ответов и сохраняет результат в кэше.
    Последующие вызовы возвращают кэшированную схему.

    Returns
    -------
    dict[str, Any]
        Словарь со схемой OpenAPI в формате JSON, содержащий.

    Notes
    -----
    Схема включает стандартные компоненты FastAPI, дополненные кастомными
    ошибками для различных сценариев:
    - AuthorizationError: Ошибки авторизации;
    - LoginError: Ошибки аутентификации;
    - RateLimitError: Превышение лимитов запросов;
    - RegisterError: Ошибки регистрации.

    Все настройки (название, версия, контакты) берутся из объекта `settings`.
    """
    if my_love_backend.openapi_schema:
        return my_love_backend.openapi_schema

    openapi_schema = get_openapi(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        summary=settings.APP_SUMMARY,
        description=settings.APP_DESCRIPTION,
        routes=my_love_backend.routes,
        tags=tags_metadata,
        contact={
            "name": settings.ADMIN_NAME,
            "email": settings.ADMIN_EMAIL,
        },
    )

    # добавляем кастомные схемы ошибок в документацию, чтобы работали ref
    openapi_schema["components"]["responses"] = {
        "AuthorizationError": AUTHORIZATION_ERROR_SCHEMA,
        "ChangePasswordError": CHANGE_PASSWORD_ERROR_SCHEMA,
        "ChangePasswordValidationError": CHANGE_PASSWORD_VALIDATION_ERROR_SCHEMA,
        "IdempotencyConflictError": IDEMPOTENCY_CONFLICT_ERROR_SCHEMA,
        "LoginError": LOGIN_ERROR_SCHEMA,
        "RateLimitError": RATE_LIMIT_ERROR_SCHEMA,
        "RegisterError": REGISTER_ERROR_SCHEMA,
    }

    # заменяем встроенные схемы на модифицированные (с code и detail)
    for path in openapi_schema["paths"].values():
        for method in path.values():
            if not (responses := method.get("responses", None)):
                continue

            if not (response := responses.get("422", None)):
                continue

            # кастомные (не автоматические) примеры пропускаем
            if response.get("description", None) != "Validation Error":
                continue

            response.update(
                {
                    "description": "Ошибка валидации",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ValidationErrorResponse"
                            }
                        }
                    },
                }
            )

    _ = openapi_schema["components"]["schemas"].pop("HTTPValidationError", None)
    _ = openapi_schema["components"]["schemas"].pop("ValidationError", None)

    response_schema = ValidationErrorResponse.model_json_schema(
        ref_template="#/components/schemas/{model}",
    )
    _ = response_schema.pop("$defs")

    error_schema = validation_error_definition.copy()  # type: ignore
    error_schema["title"] = "ErrorDetails"

    openapi_schema["components"]["schemas"]["ValidationErrorResponse"] = response_schema
    openapi_schema["components"]["schemas"]["ErrorDetails"] = error_schema

    my_love_backend.openapi_schema = openapi_schema
    return my_love_backend.openapi_schema


my_love_backend.openapi = custom_openapi
