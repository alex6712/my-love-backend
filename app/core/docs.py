from typing import Any

from app.core.enums import APICode

RATE_LIMIT_ERROR_SCHEMA: dict[str, Any] = {
    "description": "Достигнут лимит запросов",
    "schema": {
        "$ref": "#/components/schemas/StandardResponse",
    },
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
        },
        "X-RateLimit-Limit": {
            "description": "Заявленный лимит запросов в минуту",
            "schema": {"type": "integer"},
        },
        "X-RateLimit-Remaining": {
            "description": "Оставшийся лимит запросов в минуту",
            "schema": {"type": "integer"},
        },
        "X-RateLimit-Reset": {
            "description": "Временная метка сброса лимита запросов",
            "schema": {"type": "integer"},
        },
    },
}
"""OpenAPI пример ошибки превышения количества запросов в минуту."""

RATE_LIMIT_ERROR_REF: dict[str, Any] = {
    "$ref": "#/components/responses/RateLimitError",
}
"""Ссылка на схему ошибки превышения количества запросов внутри OAS."""

REGISTER_ERROR_SCHEMA: dict[str, Any] = {
    "description": "Имя пользователя или пароль не прошли валидацию",
    "content": {
        "application/json": {
            "schema": {
                "$ref": "#/components/schemas/ValidationError",
            },
            "examples": {
                "notValidUsername": {
                    "description": "Имя пользователя имеет недопустимую длину или содержит неразрешённые символы",
                    "value": {
                        "detail": [
                            {
                                "type": "value_error",
                                "loc": ["body", "username"],
                                "msg": "Value error, Username must be 3-32 characters long and contain only letters (a-z, A-Z), numbers (0-9), underscores (_), and hyphens (-).",
                                "input": "notV@lidUsern'me",
                                "ctx": {"error": {}},
                            }
                        ]
                    },
                },
                "passwordMinLength": {
                    "description": "Пароль слишком короткий",
                    "value": {
                        "detail": [
                            {
                                "type": "value_error",
                                "loc": ["body", "password"],
                                "msg": "Value error, Password must be at least 12 characters long.",
                                "input": "a",
                                "ctx": {"error": {}},
                            }
                        ]
                    },
                },
                "uppercaseLetters": {
                    "description": "Пароль должен содержать хотя бы одну латинскую букву в верхнем регистре",
                    "value": {
                        "detail": [
                            {
                                "type": "value_error",
                                "loc": ["body", "password"],
                                "msg": "Value error, Password must contain at least one uppercase letter.",
                                "input": "aaaaaaaaaaaa",
                                "ctx": {"error": {}},
                            }
                        ]
                    },
                },
                "lowercaseLetters": {
                    "description": "Пароль должен содержать хотя бы одну латинскую букву в нижнем регистре",
                    "value": {
                        "detail": [
                            {
                                "type": "value_error",
                                "loc": ["body", "password"],
                                "msg": "Value error, Password must contain at least one lowercase letter.",
                                "input": "AAAAAAAAAAAA",
                                "ctx": {"error": {}},
                            }
                        ]
                    },
                },
                "oneDigit": {
                    "description": "Пароль должен содержать хотя бы одну цифру",
                    "value": {
                        "detail": [
                            {
                                "type": "value_error",
                                "loc": ["body", "password"],
                                "msg": "Value error, Password must contain at least one digit.",
                                "input": "AAAAAAaaaaaa",
                                "ctx": {"error": {}},
                            }
                        ]
                    },
                },
                "oneSpecialSymbol": {
                    "description": "Пароль должен содержать хотя бы один специальный символ",
                    "value": {
                        "detail": [
                            {
                                "type": "value_error",
                                "loc": ["body", "password"],
                                "msg": "Value error, Password must contain at least one special character.",
                                "input": "Aa1Aa2Aa3Aa4",
                                "ctx": {"error": {}},
                            }
                        ]
                    },
                },
                "groupError": {
                    "description": "Ошибки одновременно обнаружены и в username, и в пароле",
                    "value": {
                        "detail": [
                            {
                                "type": "value_error",
                                "loc": ["body", "username"],
                                "msg": "Value error, Username must be 3-32 characters long and contain only letters (a-z, A-Z), numbers (0-9), underscores (_), and hyphens (-).",
                                "input": "xxx_re@ll'_c00|_xxx",
                                "ctx": {"error": {}},
                            },
                            {
                                "type": "value_error",
                                "loc": ["body", "password"],
                                "msg": "Value error, Password must contain at least one uppercase letter.",
                                "input": "not_secure_at_all",
                                "ctx": {"error": {}},
                            },
                        ]
                    },
                },
            },
        }
    },
}
"""OpenAPI пример ошибки при вводе недопустимых значений значений username и password."""

REGISTER_ERROR_REF: dict[str, Any] = {
    "$ref": "#/components/responses/RegisterError",
}
"""Ссылка на схему ошибки ввода недопустимых значений значений username и password внутри OAS."""

LOGIN_ERROR_SCHEMA: dict[str, Any] = {
    "description": "Неверное имя пользователя или пароль",
    "schema": {
        "$ref": "#/components/schemas/StandardResponse",
    },
    "content": {
        "application/json": {
            "example": {
                "value": {
                    "code": APICode.INCORRECT_USERNAME_PASSWORD,
                    "detail": "Incorrect username or password.",
                }
            }
        }
    },
}
"""OpenAPI пример ошибки при входе в систему."""

LOGIN_ERROR_REF: dict[str, Any] = {
    "$ref": "#/components/responses/LoginError",
}
"""Ссылка на схему ошибки входа в систему внутри OAS."""

AUTHORIZATION_ERROR_SCHEMA: dict[str, Any] = {
    "description": "Ошибка при проверке JSON Web Token",
    "schema": {
        "$ref": "#/components/schemas/StandardResponse",
    },
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
            }
        }
    },
    "headers": {
        "WWW-Authenticate": {
            "description": "Схема аутентификации",
            "schema": {"type": "string"},
        }
    },
}
"""OpenAPI примеры ошибок авторизации пользователя."""

AUTHORIZATION_ERROR_REF: dict[str, Any] = {
    "$ref": "#/components/responses/AuthorizationError",
}
"""Ссылка на схему ошибки авторизации пользователя внутри OAS."""

# TODO: Idempotency error для /files/upload
