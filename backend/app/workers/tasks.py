"""Dramatiq actors for background task execution."""

import asyncio

import dramatiq
import structlog

from app.core.queue import configure_broker

# Ensure the shared broker is registered before actors are declared.
configure_broker()

logger = structlog.get_logger(__name__)


async def sample_async_task(message: str) -> None:
    """Run a sample async task."""
    logger.info('executing_async_task', message=message)
    await asyncio.sleep(1)
    logger.info('completed_async_task')


@dramatiq.actor(max_retries=3)
def sample_task(message: str) -> None:
    """Bridge a Dramatiq actor to async application code."""
    logger.info('actor_received_job', actor='sample_task')
    asyncio.run(sample_async_task(message))
