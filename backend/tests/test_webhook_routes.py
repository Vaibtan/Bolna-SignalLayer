"""Route tests for the Bolna webhook endpoint."""

import pytest
from conftest import FakeRedis, FakeSession, load_fixture
from httpx import AsyncClient

from app.api import webhooks as webhooks_module


def _stub_infra(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stub get_redis_client and get_session_factory in the
    webhooks module so the route never touches real infra."""
    monkeypatch.setattr(
        webhooks_module,
        "get_redis_client",
        lambda: FakeRedis(),
    )
    monkeypatch.setattr(
        webhooks_module,
        "get_session_factory",
        lambda: lambda: FakeSession(),
    )


@pytest.mark.asyncio
async def test_webhook_returns_200_on_valid_payload(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
) -> None:
    payload = load_fixture(
        "bolna_webhook_completed.json",
    )
    _stub_infra(monkeypatch)

    async def fake_process(
        *_a: object, **_kw: object,
    ) -> bool:
        return True

    monkeypatch.setattr(
        webhooks_module,
        "process_bolna_event",
        fake_process,
    )

    response = await client.post(
        "/api/webhooks/bolna",
        json=payload,
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_webhook_returns_400_on_invalid_json(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/webhooks/bolna",
        content=b"not json",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_webhook_returns_200_on_duplicate(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
) -> None:
    """Duplicate events still get 200 (safe ack)."""
    payload = load_fixture(
        "bolna_webhook_completed.json",
    )
    _stub_infra(monkeypatch)

    async def fake_process(
        *_a: object, **_kw: object,
    ) -> bool:
        return False

    monkeypatch.setattr(
        webhooks_module,
        "process_bolna_event",
        fake_process,
    )

    response = await client.post(
        "/api/webhooks/bolna",
        json=payload,
    )

    assert response.status_code == 200
