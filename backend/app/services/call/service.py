"""Call initiation service with rate limiting and adapter orchestration."""

import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from redis.asyncio import Redis
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, RateLimitError
from app.models.action_recommendation import ActionRecommendation
from app.models.call_event import CallEvent
from app.models.call_session import CallSession
from app.models.deal import Deal
from app.models.evidence_anchor import EvidenceAnchor
from app.models.extraction_snapshot import ExtractionSnapshot
from app.models.followup_draft import FollowupDraft
from app.models.memory_document import MemoryDocument
from app.models.stakeholder import Stakeholder
from app.models.transcript_utterance import TranscriptUtterance
from app.services.bolna.adapter import (
    BolnaAdapter,
    CallRequest,
)

logger = structlog.get_logger(__name__)
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+|\n+")
_TOPIC_BOUNDARY = re.compile(r"[\r\n;]+")
_REDACTED_TEXT = "[REDACTED]"
_REDACTED_JSON: dict[str, object] = {"redacted": True}


def _user_rate_limit_key(user_id: uuid.UUID) -> str:
    """Return the Redis key for per-user call initiation quota."""
    settings = get_settings()
    return (
        f"{settings.REDIS_RATE_LIMIT_PREFIX}"
        f":call_init:user:{user_id}"
    )


def _stakeholder_cooldown_key(
    stakeholder_id: uuid.UUID,
) -> str:
    """Return the Redis key for stakeholder call cooldown."""
    settings = get_settings()
    return (
        f"{settings.REDIS_RATE_LIMIT_PREFIX}"
        f":call_init:stakeholder:{stakeholder_id}"
    )


async def _acquire_user_slot(
    redis: Redis,
    user_id: uuid.UUID,
) -> None:
    """Atomically INCR the user counter; raise if over quota.

    INCR is atomic — concurrent requests each get a unique
    monotonic value, so two requests cannot both slip through.
    """
    settings = get_settings()
    key = _user_rate_limit_key(user_id)
    pipe = redis.pipeline()
    pipe.incr(key)
    pipe.expire(key, settings.CALL_INIT_WINDOW_SECONDS)
    results = await pipe.execute()
    count = results[0]

    limit = settings.CALL_INIT_MAX_PER_USER_WINDOW
    if count > limit:
        ttl = await redis.ttl(key)
        raise RateLimitError(retry_after=max(ttl, 1))


async def _acquire_stakeholder_slot(
    redis: Redis,
    stakeholder_id: uuid.UUID,
) -> None:
    """SET NX the stakeholder cooldown key; raise if exists.

    SET NX is atomic — only one concurrent caller can succeed.
    """
    settings = get_settings()
    key = _stakeholder_cooldown_key(stakeholder_id)
    cooldown = settings.CALL_INIT_STAKEHOLDER_COOLDOWN_SECONDS
    was_set = await redis.set(
        key, "1", nx=True, ex=cooldown,
    )
    if not was_set:
        ttl = await redis.ttl(key)
        raise RateLimitError(retry_after=max(ttl, 1))


async def _release_user_slot(
    redis: Redis,
    user_id: uuid.UUID,
) -> None:
    """Release a reserved user slot after provider-side failure."""
    key = _user_rate_limit_key(user_id)
    current = await redis.get(key)
    if current is None:
        return

    next_value = await redis.decr(key)
    if next_value <= 0:
        await redis.delete(key)


async def _release_stakeholder_slot(
    redis: Redis,
    stakeholder_id: uuid.UUID,
) -> None:
    """Release a reserved stakeholder cooldown after provider-side failure."""
    await redis.delete(_stakeholder_cooldown_key(stakeholder_id))


def enqueue_poll(call_session_id: str) -> None:
    """Enqueue the polling fallback actor.

    Lazy import avoids triggering broker configuration
    at module load time.
    """
    from app.workers.tasks import poll_execution_status

    poll_execution_status.send(call_session_id)


def _normalize_text(value: str) -> str:
    """Collapse repeated whitespace into single spaces."""
    return " ".join(value.split())


def _cap_sentences(
    text: str,
    max_sentences: int,
) -> str:
    """Return text truncated to at most ``max_sentences`` sentences."""
    normalized = _normalize_text(text)
    if not normalized:
        return ""

    segments = [
        segment.strip()
        for segment in _SENTENCE_BOUNDARY.split(normalized)
        if segment.strip()
    ]
    if not segments:
        return normalized
    return " ".join(segments[:max_sentences])


def _extract_open_questions(
    topics: str | None,
) -> list[str] | None:
    """Normalize free-form topic notes into up to two questions."""
    if not topics:
        return None

    normalized = topics.replace("?", "?\n")
    questions = [
        _normalize_text(part.rstrip(" ?")) + "?"
        if not part.rstrip().endswith("?")
        else _normalize_text(part)
        for part in _TOPIC_BOUNDARY.split(normalized)
        if _normalize_text(part)
    ]
    if not questions:
        return None
    return questions[:2]


async def _latest_extraction_summary(
    db: AsyncSession,
    stakeholder_id: uuid.UUID,
) -> str | None:
    """Return the latest extraction summary for this stakeholder, if any."""
    row = await db.execute(
        select(ExtractionSnapshot.summary)
        .join(
            CallSession,
            CallSession.id == ExtractionSnapshot.call_session_id,
        )
        .where(
            CallSession.stakeholder_id == stakeholder_id,
            ExtractionSnapshot.summary.is_not(None),
        )
        .order_by(ExtractionSnapshot.created_at.desc())
    )
    summary = row.scalar_one_or_none()
    if isinstance(summary, str) and summary.strip():
        return _cap_sentences(summary, max_sentences=2)
    return None


async def _build_user_data(
    db: AsyncSession,
    deal: Deal,
    stakeholder: Stakeholder,
    objective: str,
    topics: str | None,
) -> dict[str, object]:
    """Build the user_data payload for the Bolna call."""
    deal_context = _cap_sentences(
        deal.summary_current
        or f"{deal.name}. {deal.stage} stage engagement.",
        max_sentences=3,
    )
    open_questions = _extract_open_questions(topics)
    known_context = await _latest_extraction_summary(
        db, stakeholder.id,
    )
    if known_context is None and stakeholder.stance_current:
        known_context = _cap_sentences(
            f"Current stance: {stakeholder.stance_current}.",
            max_sentences=1,
        )

    data: dict[str, object] = {
        "stakeholder_name": stakeholder.name,
        "stakeholder_title": stakeholder.title or "",
        "company_name": deal.account_name,
        "deal_context": deal_context,
        "call_objective": objective,
    }
    if open_questions:
        data["open_questions"] = open_questions
    if known_context:
        data["known_context"] = known_context
    return data


async def initiate_call(
    db: AsyncSession,
    redis: Redis,
    adapter: BolnaAdapter,
    org_id: uuid.UUID,
    deal_id: uuid.UUID,
    user_id: uuid.UUID,
    stakeholder_id: uuid.UUID,
    objective: str,
    topics: str | None = None,
) -> CallSession:
    """Validate, rate-limit, persist, then invoke the adapter."""
    # 1. Verify deal belongs to org
    row = await db.execute(
        select(Deal).where(
            Deal.id == deal_id,
            Deal.org_id == org_id,
        )
    )
    deal: Deal | None = row.scalar_one_or_none()
    if deal is None:
        raise NotFoundError("Deal not found.")

    # 2. Verify stakeholder belongs to deal
    sh_row = await db.execute(
        select(Stakeholder).where(
            Stakeholder.id == stakeholder_id,
            Stakeholder.deal_id == deal_id,
        )
    )
    sh: Stakeholder | None = sh_row.scalar_one_or_none()
    if sh is None:
        raise NotFoundError("Stakeholder not found.")

    if not sh.phone:
        raise NotFoundError(
            "Stakeholder has no phone number on file.",
        )

    # 3. Atomic rate limiting — reserve slots BEFORE the
    # external call.  INCR / SET-NX are individually atomic
    # so concurrent requests cannot both slip through.
    await _acquire_user_slot(redis, user_id)
    try:
        await _acquire_stakeholder_slot(redis, stakeholder_id)
    except Exception:
        await _release_user_slot(redis, user_id)
        raise

    # 4. Build call request
    settings = get_settings()
    user_data = await _build_user_data(
        db,
        deal,
        sh,
        objective,
        topics,
    )
    provider_request: dict[str, Any] = {
        "agent_id": settings.BOLNA_AGENT_ID,
        "recipient_phone_number": sh.phone,
        "user_data": user_data,
    }
    call_request = CallRequest(
        agent_id=str(provider_request["agent_id"]),
        recipient_phone_number=str(
            provider_request["recipient_phone_number"]
        ),
        user_data=user_data,
    )

    # 5. Persist the CallSession and COMMIT before the
    # external side-effect.  If the process dies after
    # Bolna accepts but before our update, the durable
    # "initiating" row lets webhook / polling recover.
    session = CallSession(
        deal_id=deal_id,
        stakeholder_id=stakeholder_id,
        provider_name="bolna",
        status="initiating",
        processing_status="pending",
        objective=objective,
        initiated_by_user_id=user_id,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    # 6. Call the provider
    call_response = await adapter.initiate_call(call_request)

    # 7. Update session with provider response
    if call_response.success:
        session.provider_call_id = (
            call_response.provider_call_id
        )
        session.status = "queued"
        session.provider_metadata_json = (
            {
                "request": provider_request,
                "response": call_response.raw_response,
            }
        )

        logger.info(
            "call.initiated",
            call_session_id=str(session.id),
            provider_call_id=(
                call_response.provider_call_id
            ),
        )
    else:
        await _release_stakeholder_slot(redis, stakeholder_id)
        await _release_user_slot(redis, user_id)
        session.status = "failed"
        session.provider_metadata_json = (
            {
                "request": provider_request,
                "response": call_response.raw_response,
                "error": call_response.error_message,
            }
        )
        logger.warning(
            "call.initiation_failed",
            call_session_id=str(session.id),
            error=call_response.error_message,
        )

    return session


async def get_call_session(
    db: AsyncSession,
    org_id: uuid.UUID,
    call_id: uuid.UUID,
) -> CallSession:
    """Fetch a call session by ID (org-scoped via deal JOIN)."""
    row = await db.execute(
        select(CallSession)
        .join(Deal, Deal.id == CallSession.deal_id)
        .where(
            CallSession.id == call_id,
            Deal.org_id == org_id,
        )
    )
    cs: CallSession | None = row.scalar_one_or_none()
    if cs is None:
        raise NotFoundError("Call session not found.")
    return cs


async def _redact_call_artifacts_batch(
    db: AsyncSession,
    call_ids: list[uuid.UUID],
) -> None:
    """Scrub transcript-derived artifacts for one or more calls."""
    if not call_ids:
        return

    await db.execute(
        delete(TranscriptUtterance).where(
            TranscriptUtterance.call_session_id.in_(call_ids)
        )
    )
    await db.execute(
        update(EvidenceAnchor)
        .where(EvidenceAnchor.call_session_id.in_(call_ids))
        .values(
            transcript_utterance_id=None,
            quote_text=_REDACTED_TEXT,
        )
    )
    await db.execute(
        update(ExtractionSnapshot)
        .where(
            ExtractionSnapshot.call_session_id.in_(call_ids)
        )
        .values(
            extracted_json=_REDACTED_JSON,
            summary=_REDACTED_TEXT,
        )
    )
    await db.execute(
        update(MemoryDocument)
        .where(MemoryDocument.call_session_id.in_(call_ids))
        .values(
            content=_REDACTED_TEXT,
            metadata_json=_REDACTED_JSON,
            embedding=None,
        )
    )
    await db.execute(
        update(FollowupDraft)
        .where(FollowupDraft.call_session_id.in_(call_ids))
        .values(
            subject=_REDACTED_TEXT,
            body_text=_REDACTED_TEXT,
        )
    )
    await db.execute(
        update(ActionRecommendation)
        .where(
            ActionRecommendation.call_session_id.in_(call_ids)
        )
        .values(
            reason=_REDACTED_TEXT,
            payload_json=_REDACTED_JSON,
        )
    )
    await db.execute(
        update(CallSession)
        .where(CallSession.id.in_(call_ids))
        .values(
            transcript_redacted=True,
            recording_url=None,
            updated_at=func.now(),
        )
    )


async def redact_call_artifacts(
    db: AsyncSession,
    call_id: uuid.UUID,
) -> None:
    """Redact transcript-derived artifacts for a single call."""
    await _redact_call_artifacts_batch(db, [call_id])
    await db.commit()


async def apply_transcript_retention(
    db: AsyncSession,
) -> int:
    """Redact expired transcript artifacts per retention policy."""
    settings = get_settings()
    cutoff = datetime.now(timezone.utc) - timedelta(
        days=settings.TRANSCRIPT_RETENTION_DAYS,
    )
    result = await db.execute(
        select(CallSession.id).where(
            CallSession.ended_at.is_not(None),
            CallSession.ended_at < cutoff,
            CallSession.transcript_redacted.is_(False),
        )
    )
    expired_call_ids = list(result.scalars().all())
    if not expired_call_ids:
        return 0

    await _redact_call_artifacts_batch(db, expired_call_ids)
    await db.commit()
    logger.info(
        "transcript.retention_applied",
        redacted_call_count=len(expired_call_ids),
        cutoff=cutoff.isoformat(),
    )
    return len(expired_call_ids)


async def get_call_transcript(
    db: AsyncSession,
    org_id: uuid.UUID,
    call_id: uuid.UUID,
) -> list[TranscriptUtterance]:
    """Return transcript utterances for a call (org-scoped)."""
    # Verify the call belongs to the org first.
    await get_call_session(db, org_id, call_id)

    result = await db.execute(
        select(TranscriptUtterance)
        .where(TranscriptUtterance.call_session_id == call_id)
        .order_by(TranscriptUtterance.sequence_number)
    )
    return list(result.scalars().all())


async def get_call_timeline(
    db: AsyncSession,
    org_id: uuid.UUID,
    call_id: uuid.UUID,
) -> list[CallEvent]:
    """Return call events for a timeline view (org-scoped)."""
    await get_call_session(db, org_id, call_id)

    result = await db.execute(
        select(CallEvent)
        .options(load_only(
            CallEvent.id,
            CallEvent.call_session_id,
            CallEvent.provider_event_id,
            CallEvent.event_type,
            CallEvent.event_timestamp,
            CallEvent.sequence_number,
            CallEvent.created_at,
        ))
        .where(CallEvent.call_session_id == call_id)
        .order_by(
            CallEvent.event_timestamp,
            CallEvent.created_at,
            CallEvent.id,
        )
    )
    return list(result.scalars().all())
