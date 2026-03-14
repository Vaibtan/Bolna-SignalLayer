"""Dramatiq broker configuration for worker processes."""

import json
import time
from functools import lru_cache
from typing import Any

import dramatiq
import structlog
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware.current_message import CurrentMessage
from structlog.contextvars import bind_contextvars, clear_contextvars

from app.core.config import get_settings

logger = structlog.get_logger(__name__)


class JobContextMiddleware(dramatiq.Middleware):
    """Bind job metadata into structlog context for worker logs."""

    def before_process_message(
        self,
        broker: dramatiq.Broker,
        message: Any,
    ) -> None:
        del broker
        bind_contextvars(
            job_id=message.message_id,
            actor_name=message.actor_name,
        )

    def after_process_message(
        self,
        broker: dramatiq.Broker,
        message: Any,
        *,
        result: Any = None,
        exception: BaseException | None = None,
    ) -> None:
        del broker, message, result, exception
        clear_contextvars()


class DeadLetterMiddleware(dramatiq.Middleware):
    """Persist and log jobs that exhaust their retry policy.

    Writes failed job metadata to a Redis list for later
    inspection and replay via admin tooling.
    """

    _DLQ_KEY = "dealgraph:dead_letter_queue"

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
            args=message.args,
        )

        # Best-effort persist to Redis DLQ.
        try:
            import redis as _redis

            settings = get_settings()
            r = _redis.Redis.from_url(settings.REDIS_URL)
            entry = json.dumps({
                "message_id": message.message_id,
                "actor_name": message.actor_name,
                "queue_name": message.queue_name,
                "args": message.args,
                "kwargs": message.kwargs,
                "options": message.options,
                "failed_at": time.time(),
            })
            r.lpush(self._DLQ_KEY, entry)
            # Keep only last 1000 entries.
            r.ltrim(self._DLQ_KEY, 0, 999)
            r.close()
        except Exception:
            logger.warning(
                "dead_letter.persist_failed",
                exc_info=True,
            )


@lru_cache(maxsize=1)
def configure_broker() -> RedisBroker:
    """Create and register the shared Dramatiq Redis broker."""
    settings = get_settings()
    broker = RedisBroker(  # type: ignore[no-untyped-call]  # Third-party API.
        url=settings.REDIS_URL,
    )
    broker.add_middleware(CurrentMessage())
    broker.add_middleware(JobContextMiddleware())
    broker.add_middleware(DeadLetterMiddleware())
    dramatiq.set_broker(broker)
    return broker


def get_worker_threads() -> int:
    """Return the configured max concurrent pipelines.

    The CLI should start Dramatiq with:
      dramatiq app.workers.tasks --threads N
    where N is this value.
    """
    settings = get_settings()
    return settings.WORKER_MAX_CONCURRENT_PIPELINES
