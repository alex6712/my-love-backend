"""Автоматический импортёр моделей SQLAlchemy для Alembic-миграций.

Следующий код обеспечивает автоматическое обнаружение и регистрацию всех моделей,
наследующихся от BaseModel, что необходимо для корректной работы Alembic.

При импорте данного модуля происходит сканирование всех Python-файлов
в текущем каталоге и автоматический импорт определённых в них моделей.

Notes
-----
Принцип работы:
1. Сканирование текущего каталога на наличие Python-модулей;
2. Исключение специальных файлов (`__init__.py`, `base.py`);
3. Динамический импорт каждого обнаруженного модуля;
4. Поиск в модуле классов, наследующих от `BaseModel`;
5. Добавление найденных классов в глобальное пространство имён.

Это позволяет Alembic автоматически видеть все модели без необходимости
явного импорта каждой модели в `__init__.py`. При добавлении новой модели
достаточно создать файл с классом, наследующимся от `BaseModel`, и он будет
обнаружен при следующем запуске.
"""

import importlib
import pkgutil
from pathlib import Path

from .base import BaseModel

package_dir = Path(__file__).resolve().parent
modules = pkgutil.iter_modules([str(package_dir)])

for _, module_name, is_pkg in modules:
    if module_name == "__init__" or module_name == "base" or is_pkg:
        continue

    module = importlib.import_module(f".{module_name}", package=__package__)

    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if (
            hasattr(attr, "__bases__")
            and BaseModel in attr.__bases__
            or (hasattr(attr, "__mro__") and BaseModel in attr.__mro__)
        ):
            globals()[attr_name] = attr

__all__ = [name for name in globals() if not name.startswith("_")]  # type: ignore
