"""Dramatiq broker configuration for worker processes."""

from functools import lru_cache
from typing import Any

import dramatiq
import structlog
from dramatiq.brokers.redis import RedisBroker

from app.core.config import get_settings

logger = structlog.get_logger(__name__)


class DeadLetterMiddleware(dramatiq.Middleware):
    """Log jobs that were skipped after exhausting retry policy."""

    def after_skip_message(
        self,
        broker: dramatiq.Broker,
        message: Any,
    ) -> None:
        logger.error(
            'message_exhausted_retries',
            broker=type(broker).__name__,
            message_id=message.message_id,
            actor_name=message.actor_name,
        )


@lru_cache(maxsize=1)
def configure_broker() -> RedisBroker:
    """Create and register the shared Dramatiq Redis broker."""
    settings = get_settings()
    broker = RedisBroker(  # type: ignore[no-untyped-call]  # Third-party API.
        url=settings.REDIS_URL,
    )
    broker.add_middleware(DeadLetterMiddleware())
    dramatiq.set_broker(broker)
    return broker
