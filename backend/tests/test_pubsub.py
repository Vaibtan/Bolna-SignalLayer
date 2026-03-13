"""Tests for the realtime pub/sub helpers."""

import json

import pytest
from conftest import FakeRedis

from app.services.realtime.pubsub import (
    call_channel,
    deal_channel,
    notify_call_update,
    publish_event,
)


def test_deal_channel_format() -> None:
    assert deal_channel("abc") == "dealgraph:realtime:deal:abc"


def test_call_channel_format() -> None:
    assert call_channel("xyz") == "dealgraph:realtime:call:xyz"


@pytest.mark.asyncio
async def test_publish_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """publish_event sends JSON to the Redis channel."""
    published: list[tuple[str, str]] = []

    class TrackingRedis(FakeRedis):
        async def publish(
            self, channel: str, message: str,
        ) -> int:
            published.append((channel, message))
            return 1

    monkeypatch.setattr(
        "app.services.realtime.pubsub.get_redis_client",
        lambda: TrackingRedis(),
    )

    await publish_event("ch1", {"type": "test"})

    assert len(published) == 1
    assert published[0][0] == "ch1"
    assert json.loads(published[0][1]) == {"type": "test"}


@pytest.mark.asyncio
async def test_publish_event_swallows_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Publish failures are logged but never raised."""

    class BrokenRedis(FakeRedis):
        async def publish(
            self, _channel: str, _message: str,
        ) -> int:
            raise ConnectionError("redis down")

    monkeypatch.setattr(
        "app.services.realtime.pubsub.get_redis_client",
        lambda: BrokenRedis(),
    )

    # Should not raise
    await publish_event("ch1", {"type": "test"})


@pytest.mark.asyncio
async def test_notify_call_update(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """notify_call_update publishes to both call and deal channels."""
    published: list[tuple[str, str]] = []

    class TrackingRedis(FakeRedis):
        async def publish(
            self, channel: str, message: str,
        ) -> int:
            published.append((channel, message))
            return 1

    monkeypatch.setattr(
        "app.services.realtime.pubsub.get_redis_client",
        lambda: TrackingRedis(),
    )

    await notify_call_update(
        call_id="c1",
        deal_id="d1",
        event_type="call.completed",
    )

    assert len(published) == 2
    channels = {p[0] for p in published}
    assert call_channel("c1") in channels
    assert deal_channel("d1") in channels

    payload = json.loads(published[0][1])
    assert payload["type"] == "call.completed"
    assert payload["call_id"] == "c1"
    assert payload["deal_id"] == "d1"
