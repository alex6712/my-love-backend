import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.config import Settings, get_settings
from app.main import my_love_backend

settings: Settings = get_settings()


@pytest_asyncio.fixture
async def async_client():
    async with AsyncClient(
        transport=ASGITransport(app=my_love_backend),
        base_url=f"http://0.0.0.0:8000/{settings.CURRENT_API_PATH}",
    ) as client:
        yield client
