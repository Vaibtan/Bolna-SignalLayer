"""Dramatiq actors for background task execution."""

import asyncio

import dramatiq
import structlog

from app.core.queue import configure_broker

# Ensure the shared broker is registered before actors are declared.
configure_broker()

logger = structlog.get_logger(__name__)


async def _poll_execution(call_session_id: str) -> None:
    """Poll Bolna for execution status until terminal or max attempts."""
    from sqlalchemy import select

    from app.core.config import get_settings
    from app.core.redis import get_redis_client
    from app.db.session import get_session_factory
    from app.models.call_session import CallSession
    from app.services.bolna.adapter import get_bolna_adapter
    from app.services.bolna.ingestion import (
        _TERMINAL_STATUSES,
        process_bolna_event,
    )

    settings = get_settings()
    adapter = get_bolna_adapter()
    redis = get_redis_client()
    session_factory = get_session_factory()

    # Resolve provider_call_id from the session
    async with session_factory() as db:
        row = await db.execute(
            select(CallSession).where(
                CallSession.id == call_session_id,
            )
        )
        cs = row.scalar_one_or_none()
        if cs is None or not cs.provider_call_id:
            logger.warning(
                "poll.no_session",
                call_session_id=call_session_id,
            )
            return
        execution_id = cs.provider_call_id

    interval = settings.BOLNA_EXECUTION_POLL_INTERVAL_SECONDS
    max_attempts = settings.BOLNA_EXECUTION_POLL_MAX_ATTEMPTS

    for attempt in range(1, max_attempts + 1):
        await asyncio.sleep(interval)

        payload = await adapter.get_execution(execution_id)

        async with session_factory() as db:
            # Check if already terminal before processing
            row = await db.execute(
                select(CallSession).where(
                    CallSession.id == call_session_id,
                )
            )
            cs_check = row.scalar_one_or_none()
            if cs_check and cs_check.status in _TERMINAL_STATUSES:
                logger.info(
                    "poll.already_terminal",
                    call_session_id=call_session_id,
                    status=cs_check.status,
                    attempt=attempt,
                )
                return

            processed = await process_bolna_event(
                db=db,
                redis=redis,
                raw_payload=payload,
                source="polling",
            )

        logger.info(
            "poll.attempt",
            call_session_id=call_session_id,
            attempt=attempt,
            processed=processed,
            provider_status=payload.get("status"),
        )

        raw_status = payload.get("status", "")
        if raw_status in _TERMINAL_STATUSES or raw_status in {
            "in-progress",
        }:
            # in-progress is not terminal but indicates
            # we got through; terminal statuses stop polling.
            pass
        if raw_status in _TERMINAL_STATUSES:
            return

    logger.warning(
        "poll.max_attempts_reached",
        call_session_id=call_session_id,
        max_attempts=max_attempts,
    )


@dramatiq.actor(max_retries=3)
def poll_execution_status(
    call_session_id: str,
) -> None:
    """Background actor: poll Bolna for execution updates."""
    asyncio.run(_poll_execution(call_session_id))
