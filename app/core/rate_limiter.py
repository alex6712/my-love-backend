from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import Settings, get_settings

settings: Settings = get_settings()

limiter: Limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL.unicode_string(),
)
"""Экземпляр RateLimiter с настройками проекта.

Использует Redis для хранения счётчиков запросов,
что обеспечивает корректную работу в распределённых системах.
"""

LOGIN_LIMIT: str = "10/minute"
"""Ограничение на количество попыток аутентификации.

Значение: 10 запросов в минуту на один IP-адрес.
Применяется к эндпоинту /auth/login для защиты от перебора паролей.
"""

REGISTER_LIMIT: str = "5/minute"
"""Ограничение на количество регистраций.

Значение: 5 запросов в минуту на один IP-адрес.
Применяется к эндпоинту /auth/register для предотвращения
массовой регистрации аккаунтов.
"""

REFRESH_LIMIT: str = "20/minute"
"""Ограничение на количество обновлений токенов.

Значение: 20 запросов в минуту на один IP-адрес.
Применяется к эндпоинту /auth/refresh для защиты от атак
с использованием украденных refresh-токенов.
"""
