from typing import Any

from app.core.consts import (
    DISPLAY_NAME_MAX_LENGTH,
    DISPLAY_NAME_MIN_LENGTH,
    PASSWORD_MIN_LENGTH,
    USERNAME_MAX_LENGTH,
    USERNAME_MIN_LENGTH,
)
from app.core.enums import APICode

RATE_LIMIT_ERROR_SCHEMA: dict[str, Any] = {
    "content": {
        "application/json": {
            "schema": {
                "$ref": "#/components/schemas/StandardResponse",
            },
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
    "description": "Достигнут лимит запросов",
    "$ref": "#/components/responses/RateLimitError",
}
"""Ссылка на схему ошибки превышения количества запросов внутри OAS."""


def _get_password_validations_examples(filed_name: str) -> dict[str, Any]:
    """Формирует набор примеров ошибок валидации пароля для OpenAPI.

    Каждый пример подобран так, чтобы нарушать ровно одно правило из
    `PASSWORD_RULES`, при этом сам формат ошибки отражает реальное
    поведение `validate_password_strength`: даже при единственном
    нарушении сообщение и `ctx.errors` строятся по общей схеме
    (список из одного элемента), в которой перечисляются id и
    человекочитаемые описания всех сработавших правил.

    Parameters
    ----------
    filed_name : str
        Имя поля в теле запроса, для которого генерируются примеры
        (например, `"password"` или `"new_password"`).

    Returns
    -------
    dict[str, Any]
        Словарь примеров в формате OpenAPI `examples`.
    """

    def _single_violation_example(
        description: str, input_value: str, rule_id: str, rule_message: str
    ) -> dict[str, Any]:
        return {
            "description": description,
            "value": {
                "code": APICode.VALIDATION_ERROR,
                "detail": [
                    {
                        "type": "password_policy_violation",
                        "loc": ["body", filed_name],
                        "msg": f"Password does not meet security requirements: {rule_id}.",
                        "input": input_value,
                        "ctx": {
                            "ids": rule_id,
                            "errors": [{"id": rule_id, "message": rule_message}],
                        },
                    }
                ],
            },
        }

    return {
        "passwordMinLength": _single_violation_example(
            description="Пароль слишком короткий",
            input_value="a",
            rule_id="min_length",
            rule_message=f"Password must be at least {PASSWORD_MIN_LENGTH} characters long.",
        ),
        "noSpaceChars": _single_violation_example(
            description="Пароль не должен содержать пробельных символов",
            input_value="aaaaaaaaaaa a",
            rule_id="no_space_chars",
            rule_message="Password must not contain whitespace characters.",
        ),
        "uppercaseLetters": _single_violation_example(
            description="Пароль должен содержать хотя бы одну латинскую букву в верхнем регистре",
            input_value="aaaaaaaaaaaa1!",
            rule_id="require_uppercase",
            rule_message="Password must contain at least one uppercase letter.",
        ),
        "lowercaseLetters": _single_violation_example(
            description="Пароль должен содержать хотя бы одну латинскую букву в нижнем регистре",
            input_value="AAAAAAAAAAAA1!",
            rule_id="require_lowercase",
            rule_message="Password must contain at least one lowercase letter.",
        ),
        "oneDigit": _single_violation_example(
            description="Пароль должен содержать хотя бы одну цифру",
            input_value="AAAAAAaaaaaa!",
            rule_id="require_digit",
            rule_message="Password must contain at least one digit.",
        ),
        "oneSpecialSymbol": _single_violation_example(
            description="Пароль должен содержать хотя бы один специальный символ",
            input_value="Aa1Aa2Aa3Aa4",
            rule_id="require_special_character",
            rule_message="Password must contain at least one special character.",
        ),
        "multipleViolations": {
            "description": "Пароль нарушает сразу несколько правил одновременно",
            "value": {
                "code": APICode.VALIDATION_ERROR,
                "detail": [
                    {
                        "type": "password_policy_violation",
                        "loc": ["body", filed_name],
                        "msg": "Password does not meet security requirements: min_length, require_uppercase, require_digit, require_special_character.",
                        "input": "weak",
                        "ctx": {
                            "ids": "min_length, require_uppercase, require_digit, require_special_character",
                            "errors": [
                                {
                                    "id": "min_length",
                                    "message": f"Password must be at least {PASSWORD_MIN_LENGTH} characters long.",
                                },
                                {
                                    "id": "require_uppercase",
                                    "message": "Password must contain at least one uppercase letter.",
                                },
                                {
                                    "id": "require_digit",
                                    "message": "Password must contain at least one digit.",
                                },
                                {
                                    "id": "require_special_character",
                                    "message": "Password must contain at least one special character.",
                                },
                            ],
                        },
                    }
                ],
            },
        },
    }


REGISTER_ERROR_SCHEMA: dict[str, Any] = {
    "content": {
        "application/json": {
            "schema": {
                "$ref": "#/components/schemas/ValidationErrorResponse",
            },
            "examples": {
                "notValidUsername": {
                    "description": "Имя пользователя имеет недопустимую длину или содержит неразрешённые символы",
                    "value": {
                        "code": APICode.VALIDATION_ERROR,
                        "detail": [
                            {
                                "type": "value_error",
                                "loc": ["body", "username"],
                                "msg": f"Value error, Username must be {USERNAME_MIN_LENGTH}-{USERNAME_MAX_LENGTH} characters long and contain only letters (a-z, A-Z), numbers (0-9), underscores (_), and hyphens (-).",
                                "input": "notV@lidUsern'me",
                                "ctx": {"error": {}},
                            }
                        ],
                    },
                },
                "notValidDisplayName": {
                    "description": "Отображаемое имя пользователя имеет недопустимую длину",
                    "value": {
                        "code": APICode.VALIDATION_ERROR,
                        "detail": [
                            {
                                "type": "value_error",
                                "loc": ["body", "display_name"],
                                "msg": f"Value error, Display name must be {DISPLAY_NAME_MIN_LENGTH}-{DISPLAY_NAME_MAX_LENGTH} characters long.",
                                "input": "                   ",
                                "ctx": {"error": {}},
                            }
                        ],
                    },
                },
                **_get_password_validations_examples("password"),
                "groupError": {
                    "description": "Ошибки одновременно обнаружены и в username, и в пароле",
                    "value": {
                        "code": APICode.VALIDATION_ERROR,
                        "detail": [
                            {
                                "type": "value_error",
                                "loc": ["body", "username"],
                                "msg": f"Value error, Username must be {USERNAME_MIN_LENGTH}-{USERNAME_MAX_LENGTH} characters long and contain only letters (a-z, A-Z), numbers (0-9), underscores (_), and hyphens (-).",
                                "input": "xxx_re@ll'_c00|_xxx",
                                "ctx": {"error": {}},
                            },
                            {
                                "type": "password_policy_violation",
                                "loc": ["body", "password"],
                                "msg": "Password does not meet security requirements: require_uppercase, require_digit.",
                                "input": "not_secure_at_all!",
                                "ctx": {
                                    "ids": "require_uppercase, require_digit",
                                    "errors": [
                                        {
                                            "id": "require_uppercase",
                                            "message": "Password must contain at least one uppercase letter.",
                                        },
                                        {
                                            "id": "require_digit",
                                            "message": "Password must contain at least one digit.",
                                        },
                                    ],
                                },
                            },
                        ],
                    },
                },
            },
        }
    },
}
"""OpenAPI пример ошибки при вводе недопустимых значений значений username и password."""

REGISTER_ERROR_REF = {
    "description": "Имя пользователя или пароль не прошли валидацию",
    "$ref": "#/components/responses/RegisterError",
}
"""Ссылка на схему ошибки ввода недопустимых значений значений username и password внутри OAS."""

LOGIN_ERROR_SCHEMA: dict[str, Any] = {
    "content": {
        "application/json": {
            "schema": {
                "$ref": "#/components/schemas/StandardResponse",
            },
            "example": {
                "code": APICode.INCORRECT_USERNAME_PASSWORD,
                "detail": "Incorrect username or password.",
            },
        }
    },
}
"""OpenAPI пример ошибки при входе в систему."""

LOGIN_ERROR_REF = {
    "description": "Неверное имя пользователя или пароль",
    "$ref": "#/components/responses/LoginError",
}
"""Ссылка на схему ошибки входа в систему внутри OAS."""

CHANGE_PASSWORD_ERROR_SCHEMA: dict[str, Any] = {
    "content": {
        "application/json": {
            "schema": {
                "$ref": "#/components/schemas/StandardResponse",
            },
            "examples": {
                "incorrectPassword": {
                    "description": "Переданный аутентифицированным пользователем текущий пароль неверный",
                    "value": {
                        "code": APICode.INCORRECT_PASSWORD,
                        "detail": "Current password is incorrect.",
                    },
                },
                "newPasswordSameAsOld": {
                    "description": "Переданный аутентифицированным пользователем новый пароль совпадает со старым",
                    "value": {
                        "code": APICode.NEW_PASSWORD_SAME_AS_OLD,
                        "detail": "New password must differ from current.",
                    },
                },
            },
        }
    },
}
"""OpenAPI пример ошибки при попытке сменить пароль пользователя."""

CHANGE_PASSWORD_ERROR_REF = {
    "description": "Передан неверный старый пароль или новый пароль совпадает со старым",
    "$ref": "#/components/responses/ChangePasswordError",
}
"""Ссылка на схему ошибки смены пароля пользователя внутри OAS."""

CHANGE_PASSWORD_VALIDATION_ERROR_SCHEMA: dict[str, Any] = {
    "content": {
        "application/json": {
            "schema": {
                "$ref": "#/components/schemas/StandardResponse",
            },
            "examples": {
                **_get_password_validations_examples("new_password"),
                "passwordDoNotMatch": {
                    "description": "Переданный аутентифицированным пользователем новый пароль подтверждён неверно",
                    "value": {
                        "code": APICode.VALIDATION_ERROR,
                        "detail": [
                            {
                                "type": "value_error",
                                "loc": ["body"],
                                "msg": "Value error, Passwords do not match",
                                "input": {
                                    "current_password": "SecureP@ss123!",
                                    "new_password": "SecureP@ss222!",
                                    "confirm_password": "SecureP@ss333!",
                                },
                                "ctx": {"error": {}},
                            }
                        ],
                    },
                },
            },
        }
    },
}
"""OpenAPI пример ошибки валидации при попытке сменить пароль пользователя."""

CHANGE_PASSWORD_VALIDATION_ERROR_REF = {
    "description": "Новый пароль не прошёл валидацию или новый пароль подтверждён неверно",
    "$ref": "#/components/responses/ChangePasswordValidationError",
}
"""Ссылка на схему ошибки валидации смены пароля пользователя внутри OAS."""

AUTHORIZATION_ERROR_SCHEMA: dict[str, Any] = {
    "content": {
        "application/json": {
            "schema": {
                "$ref": "#/components/schemas/StandardResponse",
            },
            "examples": {
                "tokenNotPassed": {
                    "description": "Access-токен не передан в заголовке Authorization",
                    "value": {
                        "code": APICode.TOKEN_NOT_PASSED,
                        "detail": "Access token is missing. Provide it in the Authorization: Bearer <token> header.",
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
                    "description": "Подпись токена верна, но срок действия истёк",
                    "value": {
                        "code": APICode.TOKEN_SIGNATURE_EXPIRED,
                        "detail": "Signature of passed token has expired.",
                    },
                },
                "tokenRevoked": {
                    "description": "Токен доступа был отозван",
                    "value": {
                        "code": APICode.TOKEN_REVOKED,
                        "detail": "Access token has been revoked.",
                    },
                },
            },
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

AUTHORIZATION_ERROR_REF = {
    "description": "Ошибка при проверке JSON Web Token",
    "$ref": "#/components/responses/AuthorizationError",
}
"""Ссылка на схему ошибки авторизации пользователя внутри OAS."""

IDEMPOTENCY_CONFLICT_ERROR_SCHEMA: dict[str, Any] = {
    "content": {
        "application/json": {
            "schema": {
                "$ref": "#/components/schemas/StandardResponse",
            },
            "example": {
                "code": APICode.IDEMPOTENCY_CONFLICT,
                "detail": "Request already in progress.",
            },
        }
    },
}
"""OpenAPI пример конфликта идемпотентности."""

IDEMPOTENCY_CONFLICT_ERROR_REF = {
    "description": "Конфликт идемпотентности",
    "$ref": "#/components/responses/IdempotencyConflictError",
}
"""Ссылка на схему конфликта идемпотентности внутри OAS."""
