from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings, get_settings

settings: Settings = get_settings()

engine: AsyncEngine = create_async_engine(
    url=settings.POSTGRES_DSN,
    echo=False,
    pool_pre_ping=True,
)
AsyncSessionMaker: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)
