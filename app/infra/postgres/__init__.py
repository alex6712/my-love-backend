from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

settings = get_settings()

async_engine = create_async_engine(
    url=settings.POSTGRES_DSN.unicode_string(),
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=10,
)
"""SQLAlchemy async engine, который используется в этом проекте."""

AsyncSessionMaker = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)
"""Фабрика асинхронных сессий SQLAlchemy."""
