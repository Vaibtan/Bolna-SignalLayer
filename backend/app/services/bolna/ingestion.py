"""Shared Bolna event ingestion: webhook and polling both enter here."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from redis.asyncio import Redis
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.call_event import CallEvent
from app.models.call_session import CallSession
from app.services.bolna.fixture_capture import maybe_capture_payload
from app.services.realtime.pubsub import notify_call_update

logger = structlog.get_logger(__name__)

# Bolna status string → internal event type.
_STATUS_MAP: dict[str, str] = {
    "queued": "call.queued",
    "ringing": "call.ringing",
    "in-progress": "call.started",
    "in_progress": "call.started",
    "completed": "call.completed",
    "busy": "call.busy",
    "no-answer": "call.no_answer",
    "no_answer": "call.no_answer",
    "canceled": "call.canceled",
    "failed": "call.failed",
    "stopped": "call.failed",
    "error": "call.failed",
}

# Internal event type → internal CallSession.status value.
_EVENT_TO_SESSION_STATUS: dict[str, str] = {
    "call.queued": "queued",
    "call.ringing": "ringing",
    "call.started": "in_progress",
    "call.completed": "completed",
    "call.busy": "busy",
    "call.no_answer": "no_answer",
    "call.canceled": "canceled",
    "call.failed": "failed",
}

_TERMINAL_STATUSES = frozenset({
    "completed", "no_answer", "busy", "failed", "canceled",
})


def _derive_idempotency_key(
    payload: dict[str, Any],
) -> str:
    """Build a Redis idempotency key from the payload.

    Prefer an explicit event ID.  Fall back to
    execution_id + status + sha256(payload).
    """
    base = "dealgraph:webhook:bolna"

    event_id = payload.get("event_id") or payload.get("id")
    if event_id:
        return f"{base}:{event_id}"

    execution_id = _extract_execution_id(payload) or "unknown"
    status = payload.get("status", "unknown")
    digest = hashlib.sha256(
        str(sorted(payload.items())).encode()
    ).hexdigest()[:16]
    return f"{base}:{execution_id}:{status}:{digest}"


def _extract_execution_id(
    payload: dict[str, Any],
) -> str:
    """Pull the provider execution ID from the payload."""
    return str(
        payload.get("execution_id")
        or payload.get("id")
        or ""
    )


def _normalize_event_type(
    payload: dict[str, Any],
) -> str | None:
    """Map the Bolna status to an internal event type.

    Returns None for unknown statuses — they are still
    persisted as CallEvent but do not update the session.
    """
    raw_status = payload.get("status", "")
    return _STATUS_MAP.get(raw_status)


async def _check_idempotency(
    redis: Redis,
    key: str,
) -> bool:
    """Return True if this event was already processed."""
    settings = get_settings()
    was_set = await redis.set(
        key, "1",
        nx=True,
        ex=settings.WEBHOOK_IDEMPOTENCY_TTL_SECONDS,
    )
    return not was_set


async def _resolve_session(
    db: AsyncSession,
    execution_id: str,
) -> CallSession | None:
    """Find the CallSession by provider_call_id."""
    if not execution_id:
        return None
    row = await db.execute(
        select(CallSession).where(
            CallSession.provider_call_id == execution_id,
        )
    )
    return row.scalar_one_or_none()


async def _append_event(
    db: AsyncSession,
    session_id: uuid.UUID,
    event_type: str,
    payload: dict[str, Any],
    provider_event_id: str | None,
) -> CallEvent:
    """Append a CallEvent row."""
    ts_raw = payload.get("created_at") or payload.get(
        "updated_at",
    )
    if isinstance(ts_raw, str):
        try:
            ts = datetime.fromisoformat(ts_raw)
        except ValueError:
            ts = datetime.now(timezone.utc)
    else:
        ts = datetime.now(timezone.utc)

    event = CallEvent(
        call_session_id=session_id,
        provider_event_id=provider_event_id,
        event_type=event_type,
        event_timestamp=ts,
        payload_json=payload,
    )
    db.add(event)
    await db.flush()
    return event


async def _update_session_projection(
    db: AsyncSession,
    session: CallSession,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    """Update the CallSession read-model from a normalized event."""
    new_status = _EVENT_TO_SESSION_STATUS.get(event_type)
    if not new_status:
        return

    changes: dict[str, Any] = {
        "status": new_status,
        "updated_at": func.now(),
    }

    if event_type == "call.started":
        changes["started_at"] = func.now()

    if new_status in _TERMINAL_STATUSES:
        changes["ended_at"] = func.now()
        duration = payload.get("duration")
        if duration is not None:
            changes["duration_seconds"] = int(duration)
        recording = payload.get("recording_url")
        if recording:
            changes["recording_url"] = str(recording)

    transcript = payload.get("transcript")
    if transcript and new_status in _TERMINAL_STATUSES:
        changes["processing_status"] = (
            "transcript_finalized"
        )

    await db.execute(
        update(CallSession)
        .where(CallSession.id == session.id)
        .values(**changes)
    )


async def process_bolna_event(
    db: AsyncSession,
    redis: Redis,
    raw_payload: dict[str, Any],
    source: str = "webhook",
) -> bool:
    """Shared ingestion entry point for webhooks and polling.

    Returns True if the event was processed, False if it was
    a duplicate or could not be resolved to a session.
    """
    maybe_capture_payload(raw_payload, source)
    idem_key = _derive_idempotency_key(raw_payload)

    # 1. Idempotency check
    if await _check_idempotency(redis, idem_key):
        logger.info(
            "bolna.event_duplicate",
            key=idem_key,
            source=source,
        )
        return False

    # 2. Resolve the CallSession
    execution_id = _extract_execution_id(raw_payload)
    session = await _resolve_session(db, execution_id)
    if session is None:
        # Release the idempotency key so provider retries
        # can succeed once the session row exists.
        await redis.delete(idem_key)
        logger.warning(
            "bolna.event_no_session",
            execution_id=execution_id,
            source=source,
        )
        return False

    # 3. Normalize event type
    event_type = _normalize_event_type(raw_payload)
    # Persist the raw event even for unknown statuses
    stored_type = (
        event_type
        or f"unknown.{raw_payload.get('status', 'none')}"
    )

    provider_event_id = (
        raw_payload.get("event_id")
        or raw_payload.get("id")
    )

    # 4-5. Persist event and update projection.
    # If anything fails, release the idempotency key so
    # the provider retry is not treated as a duplicate.
    try:
        await _append_event(
            db,
            session.id,
            stored_type,
            raw_payload,
            str(provider_event_id)
            if provider_event_id
            else None,
        )

        if event_type:
            await _update_session_projection(
                db, session, event_type, raw_payload,
            )

        await db.commit()
    except Exception:
        await redis.delete(idem_key)
        raise

    # 6. Publish realtime hint (best-effort, never blocks durable path).
    # Skip unknown events — they do not update the session projection,
    # so a frontend refetch would return the same data.
    if event_type:
        await notify_call_update(
            call_id=str(session.id),
            deal_id=str(session.deal_id),
            event_type=stored_type,
        )

    logger.info(
        "bolna.event_processed",
        execution_id=execution_id,
        event_type=stored_type,
        source=source,
        session_id=str(session.id),
    )
    return True
