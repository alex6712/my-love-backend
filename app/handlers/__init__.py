import importlib
import pkgutil
from pathlib import Path


def register_all_handlers() -> None:
    handlers_dir = Path(__file__).parent

    for subdir in ("client", "server", "success"):
        subpackage = f"app.handlers.{subdir}"
        subdir_path = handlers_dir / subdir

        for module_info in pkgutil.iter_modules([str(subdir_path)]):
            importlib.import_module(f"{subpackage}.{module_info.name}")
