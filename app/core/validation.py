import re
import unicodedata
from typing import Annotated

from pydantic import AfterValidator, StringConstraints
from pydantic_core import PydanticCustomError

from app.core.enums import PasswordRuleType
from app.schemas.dto.password import PasswordRuleSpec

USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")
"""Регулярное выражение для проверки формата имени пользователя.

Разрешает латинские буквы (верхний и нижний регистр),
цифры, нижнее подчёркивание и дефис.
"""

USERNAME_MIN_LENGTH = 3
"""Минимальная длина имени пользователя в символах."""

USERNAME_MAX_LENGTH = 32
"""Максимальная длина имени пользователя в символах."""

DISPLAY_NAME_MIN_LENGTH = 1
"""Минимальная длина отображаемого имени пользователя в символах."""

DISPLAY_NAME_MAX_LENGTH = 64
"""Максимальная длина отображаемого имени пользователя в символах."""

PASSWORD_MIN_LENGTH = 12
"""Минимальная длина пароля в символах."""

SPECIAL_CHAR_PATTERN = r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]"
"""Регулярное выражение для проверки наличия специальных символов."""

ValidatedUsername = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=USERNAME_MIN_LENGTH,
        max_length=USERNAME_MAX_LENGTH,
        pattern=USERNAME_PATTERN,
    ),
]
"""Типизированная аннотация для поля имени пользователя с автоматической валидацией.

Используется в Pydantic-схемах для автоматической проверки имени
пользователя при десериализации данных.
"""

PASSWORD_POLICY_VERSION = "1.1.0"
"""Текущая версия парольной политики (стратегии валиации паролей)."""

PASSWORD_RULES = [
    PasswordRuleSpec(
        id="min_length",
        description=f"Password must be at least {PASSWORD_MIN_LENGTH} characters long.",
        type=PasswordRuleType.MIN,
        value=PASSWORD_MIN_LENGTH,
        unit="characters",
        check=lambda v: len(v) >= PASSWORD_MIN_LENGTH,
    ),
    PasswordRuleSpec(
        id="no_space_characters",
        description="Password must not contain whitespace characters.",
        type=PasswordRuleType.BOOLEAN,
        value=True,
        check=lambda v: not any(char.isspace() for char in v),
    ),
    PasswordRuleSpec(
        id="require_uppercase",
        description="Password must contain at least one uppercase letter.",
        type=PasswordRuleType.BOOLEAN,
        value=True,
        check=lambda v: bool(re.search(r"[A-Z]", v)),
    ),
    PasswordRuleSpec(
        id="require_lowercase",
        description="Password must contain at least one lowercase letter.",
        type=PasswordRuleType.BOOLEAN,
        value=True,
        check=lambda v: bool(re.search(r"[a-z]", v)),
    ),
    PasswordRuleSpec(
        id="require_digit",
        description="Password must contain at least one digit.",
        type=PasswordRuleType.BOOLEAN,
        value=True,
        check=lambda v: bool(re.search(r"[0-9]", v)),
    ),
    PasswordRuleSpec(
        id="require_special_character",
        description="Password must contain at least one special character.",
        type=PasswordRuleType.BOOLEAN,
        value=True,
        check=lambda v: bool(re.search(SPECIAL_CHAR_PATTERN, v)),
    ),
    PasswordRuleSpec(
        id="special_character_set",
        description="Set of allowed special characters.",
        type=PasswordRuleType.CHARSET,
        value=SPECIAL_CHAR_PATTERN,
        check=None,
    ),
]
"""Единый источник правды для парольной политики: используется
и в `validate_password_strength` (проверка), и в эндпоинте
`GET /password-policy` (публичный контракт), чтобы исключить
дублирование и рассинхронизацию правил.
"""


def validate_password_strength(value: str) -> str:
    """Проверяет пароль на соответствие требованиям безопасности.

    Проверяет пароль сразу по всем правилам из `PASSWORD_RULES`
    (кроме информационных, у которых `check is None`) и собирает
    все нарушения в единую структурированную ошибку, чтобы
    пользователь мог исправить всё за один раз.

    Parameters
    ----------
    value : str
        Пароль в виде строки для проверки.

    Returns
    -------
    str
        Пароль, прошедший все проверки.

    Raises
    ------
    pydantic_core.PydanticCustomError
        Если пароль нарушает одно или несколько правил. В `ctx`
        ошибки передаётся список нарушенных правил вида
        `{"id": ..., "message": ...}`.
    """
    failed_rules = [
        rule
        for rule in PASSWORD_RULES
        if rule.check is not None and not rule.check(value)
    ]

    if failed_rules:
        raise PydanticCustomError(
            "password_policy_violation",
            "Password does not meet security requirements: {ids}.",
            {
                "ids": ", ".join(rule.id for rule in failed_rules),
                "errors": [
                    {"id": rule.id, "message": rule.description}
                    for rule in failed_rules
                ],
            },
        )

    return value


ValidatedPassword = Annotated[
    str,
    StringConstraints(min_length=PASSWORD_MIN_LENGTH),
    AfterValidator(validate_password_strength),
]
"""Типизированная аннотация для поля пароля с автоматической валидацией.

Используется в Pydantic-схемах для автоматической проверки пароля
при десериализации данных.
"""


def normalize_unicode_nfc(value: str) -> str:
    """Нормализует строку в каноническую форму NFC.

    Unicode допускает несколько различных представлений одного и того же
    визуального символа. Например, символ "é" может быть записан как
    единый кодовый пункт (U+00E9) либо как последовательность символов
    "e" (U+0065) и комбинируемого акцента (U+0301).

    Нормализация в форму NFC приводит эквивалентные представления к
    единому каноническому виду, что обеспечивает корректное сравнение,
    хранение и подсчёт длины строк.

    Parameters
    ----------
    value : str
        Строка для нормализации.

    Returns
    -------
    str
        Нормализованная строка в форме NFC.
    """
    return unicodedata.normalize("NFC", value)


ValidatedDisplayName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=DISPLAY_NAME_MIN_LENGTH,
        max_length=DISPLAY_NAME_MAX_LENGTH,
    ),
    AfterValidator(normalize_unicode_nfc),
]
"""Типизированная аннотация для поля отображаемого имени пользователя с автоматической валидацией.

Используется в Pydantic-схемах для автоматической проверки и нормализации
отображаемого имени пользователя при десериализации данных.
"""
