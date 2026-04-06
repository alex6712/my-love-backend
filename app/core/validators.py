import re
from typing import Annotated

from pydantic import AfterValidator

USERNAME_PATTERN: re.Pattern[str] = re.compile(r"^[a-zA-Z0-9_-]{3,32}$")
"""Регулярное выражение для проверки формата имени пользователя.

Разрешает от 3 до 32 символов, включая латинские буквы (верхний и нижний регистр),
цифры, нижнее подчёркивание и дефис.
"""

PASSWORD_MIN_LENGTH: int = 12
"""Минимальная длина пароля в символах."""


def validate_password_strength(value: str) -> str:
    """Проверяет пароль на соответствие требованиям безопасности.

    Валидация включает следующие проверки:
    - Минимальная длина: {PASSWORD_MIN_LENGTH} символов
    - Наличие символов верхнего регистра (A-Z)
    - Наличие символов нижнего регистра (a-z)
    - Наличие цифр (0-9)
    - Наличие специальных символов (!@#$%^&* и т.д.)

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
    ValueError
        Если пароль не соответствует одному из требований безопасности.
    """
    if len(value) < PASSWORD_MIN_LENGTH:
        raise ValueError(
            f"Password must be at least {PASSWORD_MIN_LENGTH} characters long."
        )

    if not re.search(r"[A-Z]", value):
        raise ValueError("Password must contain at least one uppercase letter.")

    if not re.search(r"[a-z]", value):
        raise ValueError("Password must contain at least one lowercase letter.")

    if not re.search(r"[0-9]", value):
        raise ValueError("Password must contain at least one digit.")

    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", value):
        raise ValueError("Password must contain at least one special character.")

    return value


def validate_username(value: str) -> str:
    """Проверяет имя пользователя на соответствие допустимому формату.

    Требования к имени пользователя:
    - Длина от 3 до 32 символов;
    - Разрешены только латинские буквы (a-z, A-Z), цифры (0-9),
      нижнее подчёркивание (_) и дефис (-).

    Parameters
    ----------
    value : str
        Имя пользователя для проверки.

    Returns
    -------
    str
        Имя пользователя в нижнем регистре, прошедшее проверку.

    Raises
    ------
    ValueError
        Если имя пользователя не соответствует допустимому формату.
    """
    if not USERNAME_PATTERN.match(value):
        raise ValueError(
            "Username must be 3-32 characters long and contain only "
            "letters (a-z, A-Z), numbers (0-9), underscores (_), and hyphens (-)."
        )

    return value


ValidatedPassword = Annotated[str, AfterValidator(validate_password_strength)]
"""Типизированная аннотация для поля пароля с автоматической валидацией.

Используется в Pydantic-схемах для автоматической проверки пароля
при десериализации данных.
"""

ValidatedUsername = Annotated[str, AfterValidator(validate_username)]
"""Типизированная аннотация для поля имени пользователя с автоматической валидацией.

Используется в Pydantic-схемах для автоматической проверки имени
пользователя при десериализации данных.
"""
