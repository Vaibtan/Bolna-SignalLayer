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


async def _run_extraction(call_session_id: str) -> None:
    """Run the extraction pipeline for a completed call."""
    import uuid as _uuid

    from app.db.session import get_session_factory
    from app.services.extraction.service import run_extraction

    session_factory = get_session_factory()

    async with session_factory() as db:
        snapshot = await run_extraction(
            db, _uuid.UUID(call_session_id),
        )

    if snapshot is not None:
        try:
            compute_risk.send(call_session_id)
        except Exception:
            logger.warning(
                "risk.enqueue_failed",
                call_session_id=call_session_id,
                exc_info=True,
            )


@dramatiq.actor(max_retries=2)
def extract_call(call_session_id: str) -> None:
    """Background actor: extract structured data from call."""
    asyncio.run(_run_extraction(call_session_id))


async def _run_risk(call_session_id: str) -> None:
    """Run the risk engine for a completed extraction."""
    import uuid as _uuid

    from app.db.session import get_session_factory
    from app.services.risk.service import run_risk_update

    session_factory = get_session_factory()

    async with session_factory() as db:
        result = await run_risk_update(
            db, _uuid.UUID(call_session_id),
        )

    if result is not None:
        try:
            generate_recommendations.send(call_session_id)
        except Exception:
            logger.warning(
                "recommendation.enqueue_failed",
                call_session_id=call_session_id,
                exc_info=True,
            )


@dramatiq.actor(max_retries=2)
def compute_risk(call_session_id: str) -> None:
    """Background actor: compute risk after extraction."""
    asyncio.run(_run_risk(call_session_id))


async def _run_recommendation(
    call_session_id: str,
) -> None:
    """Run the recommendation pipeline."""
    import uuid as _uuid

    from app.db.session import get_session_factory
    from app.services.recommendation.service import (
        run_recommendation,
    )

    session_factory = get_session_factory()

    async with session_factory() as db:
        recs = await run_recommendation(
            db, _uuid.UUID(call_session_id),
        )

    if recs:
        try:
            embed_memory_documents.send(call_session_id)
        except Exception:
            logger.warning(
                "memory.enqueue_failed",
                call_session_id=call_session_id,
                exc_info=True,
            )


@dramatiq.actor(max_retries=2)
def generate_recommendations(
    call_session_id: str,
) -> None:
    """Background actor: generate recommendations."""
    asyncio.run(_run_recommendation(call_session_id))


async def _run_memory(call_session_id: str) -> None:
    """Generate and embed memory documents."""
    import uuid as _uuid

    from app.db.session import get_session_factory
    from app.services.memory.service import (
        generate_memory_documents,
    )

    session_factory = get_session_factory()

    async with session_factory() as db:
        await generate_memory_documents(
            db, _uuid.UUID(call_session_id),
        )


@dramatiq.actor(max_retries=1)
def embed_memory_documents(
    call_session_id: str,
) -> None:
    """Background actor: generate and embed memory docs."""
    asyncio.run(_run_memory(call_session_id))
