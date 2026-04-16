from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

settings = get_settings()

async_postgresql_engine = create_async_engine(
    url=settings.POSTGRES_DSN.unicode_string(),
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=10,
)
"""SQLAlchemy async engine, который используется в этом проекте."""

AsyncSessionMaker = async_sessionmaker(
    bind=async_postgresql_engine, class_=AsyncSession, expire_on_commit=False
)
"""Фабрика асинхронных сессий SQLAlchemy."""


def get_constraint_name(error: Exception) -> str | None:
    """Извлекает имя ограничения базы данных из исключения.

    Пытается получить имя constraint’а (например, уникального или внешнего ключа),
    если оно доступно во вложенном оригинальном исключении (`error.orig`).

    Parameters
    ----------
    error : Exception
        Исключение, возникшее при выполнении операции с базой данных.

    Returns
    -------
    str | None
        Имя ограничения, если оно присутствует в исключении,
        иначе None.
    """
    orig = getattr(error, "orig", None)

    if orig is not None and hasattr(orig, "constraint_name"):
        return orig.constraint_name

    return None
