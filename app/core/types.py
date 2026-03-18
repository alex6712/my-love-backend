from typing import Any, Literal

from pydantic_core import core_schema

type Domain = Literal["application", "auth", "user", "couple", "media", "note"]
"""Допустимые домены/модули приложения для логирования и маршрутизации."""

type CredentialsType = Literal["password", "token"]
"""Типы учётных данных для аутентификации: пароль или токен."""

type TokenType = Literal["access", "refresh"]
"""Типы JWT-токенов: access (короткоживущий) и refresh (долгоживущий)."""

type MediaType = Literal["album", "file"]
"""Типы медиа-контента: альбом или отдельный файл."""


class Unset:
    """Sentinel-тип для различия между 'значение не передано' и None.

    Реализован как синглтон - все экземпляры являются одним и тем же объектом,
    что позволяет использовать проверку через `is` и `isinstance`.

    Notes
    -----
    Используется совместно с типом `Maybe[T]` в сигнатурах методов сервисов,
    где поле может быть намеренно не передано (в отличие от явной передачи None).
    """

    _instance = None

    def __new__(cls) -> "Unset":
        if cls._instance is None:
            cls._instance = super().__new__(cls)

        return cls._instance

    @classmethod
    def __get_pydantic_core_schema__(cls, *_: Any) -> core_schema.CoreSchema:
        """Определяет схему валидации для Pydantic v2.

        Регистрирует `Unset` как валидный тип в Pydantic, позволяя использовать
        его в аннотациях полей моделей. Схема валидирует значение через
        `isinstance(value, Unset)`, что корректно работает с синглтон-природой класса.

        Parameters
        ----------
        *_ : Any
            Позиционные аргументы, передаваемые Pydantic при построении схемы
            (`source_type` и `handler`). Игнорируются, так как схема не зависит
            от контекста и всегда одинакова.

        Returns
        -------
        core_schema.CoreSchema
            Схема типа `is-instance`, которая принимает значение если
            `isinstance(value, Unset)` возвращает `True`.
        """
        return core_schema.is_instance_schema(cls)


UNSET = Unset()
"""Единственный экземпляр `Unset`, представляющий отсутствие переданного значения."""

type Maybe[T] = T | Unset
"""Тип для параметров, которые могут быть не переданы.

Отличается от `T | None` тем, что `None` считается явно переданным значением
(например, для записи NULL в БД), тогда как `Unset` означает отсутствие намерения
изменить поле.
"""
