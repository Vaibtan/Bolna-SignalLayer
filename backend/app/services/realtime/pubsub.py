"""Redis pub/sub helpers for realtime event delivery."""

import asyncio
import json
from typing import Any

import structlog

from app.core.redis import get_redis_client

logger = structlog.get_logger(__name__)

_CHANNEL_PREFIX = "signal_layer:realtime"


def deal_channel(deal_id: str) -> str:
    """Return the Redis pub/sub channel for a deal."""
    return f"{_CHANNEL_PREFIX}:deal:{deal_id}"


def call_channel(call_id: str) -> str:
    """Return the Redis pub/sub channel for a call."""
    return f"{_CHANNEL_PREFIX}:call:{call_id}"


async def publish_event(
    channel: str,
    event: dict[str, Any],
) -> None:
    """Publish a lightweight JSON event to a Redis pub/sub channel.

    Failures are logged but never raised — realtime delivery
    is best-effort and must not break the durable write path.
    """
    redis = get_redis_client()
    try:
        await redis.publish(channel, json.dumps(event))
    except Exception:
        logger.warning(
            "realtime.publish_failed",
            channel=channel,
            exc_info=True,
        )


async def notify_call_update(
    call_id: str,
    deal_id: str,
    event_type: str,
) -> None:
    """Publish a call update to both the call and deal channels.

    Messages are lightweight hints — the frontend re-fetches
    durable state from the REST API on receipt.
    """
    payload: dict[str, Any] = {
        "type": event_type,
        "call_id": call_id,
        "deal_id": deal_id,
    }
    await asyncio.gather(
        publish_event(call_channel(call_id), payload),
        publish_event(deal_channel(deal_id), payload),
    )
