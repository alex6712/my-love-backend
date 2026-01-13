import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(async_client: AsyncClient):
    """Проверка работоспособности API."""
    response = await async_client.get("/health")

    assert response.status_code == 200
    assert response.json()["detail"] == "API works!"


@pytest.mark.asyncio
async def test_app_info(async_client: AsyncClient):
    """Проверка получения информации о приложении."""
    response = await async_client.get("/app_info")

    assert response.status_code == 200
    data = response.json()
    assert data["app_name"] == "My Love Backend"
    assert "app_version" in data
