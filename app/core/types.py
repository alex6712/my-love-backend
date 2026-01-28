from typing import Any, Literal

type Domain = Literal["application", "auth", "user", "couple", "media", "note"]
"""Допустимые домены/модули приложения для логирования и маршрутизации."""

type CredentialsType = Literal["password", "token"]
"""Типы учётных данных для аутентификации: пароль или токен."""

type TokenType = Literal["access", "refresh"]
"""Типы JWT-токенов: access (короткоживущий) и refresh (долгоживущий)."""

type Tokens = dict[TokenType, str]
"""Пара токенов доступа и обновления в виде словаря {token_type: token_value}."""

type MediaType = Literal["album", "file"]
"""Типы медиа-контента: альбом или отдельный файл."""

type Payload = dict[str, Any]
"""Универсальный словарь для произвольных данных запроса/ответа."""
