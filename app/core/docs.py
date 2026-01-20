from typing import Any

from app.core.enums import APICode
from app.schemas.v1.responses.standard import StandardResponse

RATE_LIMIT_ERROR_EXAMPLE: dict[str, Any] = {
    "description": "Достигнут лимит запросов",
    "model": StandardResponse,
    "content": {
        "application/json": {
            "example": {
                "code": APICode.RATE_LIMIT_EXCEEDED,
                "detail": "Too many requests. Please slow down.",
            },
        },
    },
    "headers": {
        "Retry-After": {
            "description": "Количество секунд до гарантированного повтора запроса",
            "schema": {"type": "integer"},
        }
    },
}
"""OpenAPI пример ошибки превышения количества запросов в минуту."""

LOGIN_ERROR_EXAMPLE: dict[str, Any] = {
    "description": "Неверное имя пользователя или пароль",
    "model": StandardResponse,
    "content": {
        "application/json": {
            "example": {
                "value": {
                    "code": APICode.INCORRECT_USERNAME_PASSWORD,
                    "detail": "Incorrect username or password.",
                },
            },
        },
    },
}
"""OpenAPI пример ошибки при входе в систему."""

AUTHORIZATION_ERROR_EXAMPLES: dict[str, Any] = {
    "description": "Ошибка при проверке JSON Web Token",
    "model": StandardResponse,
    "content": {
        "application/json": {
            "examples": {
                "tokenNotPassed": {
                    "description": "Токен не передан",
                    "value": {
                        "code": APICode.TOKEN_NOT_PASSED,
                        "detail": "${tokenType} token not found in Authorization header. Make sure to add it with Bearer scheme.",
                    },
                },
                "invalidToken": {
                    "description": "Не получается проверить подпись токена",
                    "value": {
                        "code": APICode.INVALID_TOKEN,
                        "detail": "The passed token is damaged or poorly signed.",
                    },
                },
                "tokenSignatureExpired": {
                    "description": "Подпись токена верна, но просрочена",
                    "value": {
                        "code": APICode.TOKEN_SIGNATURE_EXPIRED,
                        "detail": "Signature of passed token has expired.",
                    },
                },
            },
        },
    },
    "headers": {
        "WWW-Authenticate": {
            "description": "Схема аутентификации",
            "schema": {"type": "string"},
        }
    },
}
"""OpenAPI примеры ошибок авторизации пользователя."""
