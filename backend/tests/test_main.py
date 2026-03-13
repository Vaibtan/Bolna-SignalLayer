import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_live(client: AsyncClient) -> None:
    response = await client.get("/api/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_ready(client: AsyncClient) -> None:
    response = await client.get("/api/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_sets_request_id_header(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/health/live")
    assert response.status_code == 200
    assert response.headers["X-Request-ID"]


@pytest.mark.asyncio
async def test_health_echoes_incoming_request_id(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/api/health/live",
        headers={"X-Request-ID": "req-123"},
    )
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-123"
