import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_validation_error(async_client: AsyncClient):
    """Тест ошибки валидации при регистрации (без БД)."""
    response = await async_client.post(
        "/auth/register",
        json={"username": "ab", "password": "short"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_logout_unauthorized(async_client: AsyncClient):
    """Тест выхода без авторизации."""
    response = await async_client.post("/auth/logout")

    assert response.status_code == 401
