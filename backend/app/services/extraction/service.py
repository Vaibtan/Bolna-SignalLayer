"""Extraction pipeline: transcript → structured intelligence.

Uses Google Gemini with SDK-level structured output enforcement.
Retries validation failures with the error summary in the repair
prompt so the model can correct missing or malformed fields.
"""

from __future__ import annotations

import uuid

import structlog
from google import genai
from pydantic import ValidationError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)

from app.core.config import get_settings
from app.models.call_session import CallSession
from app.models.evidence_anchor import EvidenceAnchor
from app.models.extraction_snapshot import ExtractionSnapshot
from app.models.transcript_utterance import TranscriptUtterance
from app.services.extraction.schema import (
    PROMPT_VERSION,
    SCHEMA_VERSION,
    CallExtraction,
)

logger = structlog.get_logger(__name__)
_EXTRACTION_ELIGIBLE_STATUSES = frozenset({
    "transcript_finalized",
    "failed_retryable",
})

_EXTRACTION_PROMPT = """\
You are a structured data extraction system for B2B sales calls.

Analyze the following call transcript and extract structured \
intelligence according to the output schema.

Rules:
- Use "unknown" for any field where the transcript provides \
no evidence.
- Set confidence values between 0.0 and 1.0 based on how \
clearly the transcript supports the extracted value.
- For evidence items, provide the verbatim quote from the \
transcript and the speaker (agent or prospect).
- The sequence_number in evidence should reference the \
utterance number in the transcript (0-indexed).
- Prefer explicit statements over inferred conclusions.
- The summary should be 2-3 sentences capturing the key \
outcome.

Transcript:
{transcript}
"""

_REPAIR_PROMPT = """\
The previous extraction attempt failed validation with \
the following errors:

{errors}

Please fix the output to match the required schema. \
The original transcript is:

{transcript}
"""


def _build_transcript_text(
    utterances: list[TranscriptUtterance],
) -> str:
    """Format utterances into a labeled transcript string."""
    lines: list[str] = []
    for u in utterances:
        label = u.speaker.capitalize()
        lines.append(f"[{u.sequence_number}] {label}: {u.text}")
    return "\n".join(lines)


class RetryableExtractionError(Exception):
    """Raised when extraction should be retried by the worker."""


async def _call_gemini_with_repair(
    client: genai.Client,
    model: str,
    transcript_text: str,
    *,
    max_retries: int,
) -> CallExtraction:
    """Call Gemini with validation-aware repair retries."""
    last_errors: str | None = None

    async for attempt in AsyncRetrying(
        retry=retry_if_exception_type(ValidationError),
        stop=stop_after_attempt(max_retries + 1),
        wait=wait_fixed(1),
        reraise=True,
    ):
        with attempt:
            if last_errors:
                prompt = _REPAIR_PROMPT.format(
                    errors=last_errors,
                    transcript=transcript_text,
                )
            else:
                prompt = _EXTRACTION_PROMPT.format(
                    transcript=transcript_text,
                )

            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_json_schema": (
                        CallExtraction.model_json_schema()
                    ),
                },
            )

            text = response.text or ""
            try:
                return CallExtraction.model_validate_json(text)
            except ValidationError as exc:
                last_errors = str(exc)
                raise

    raise AssertionError("Extraction retry loop exited unexpectedly.")


async def _claim_extraction(
    db: AsyncSession,
    call_session_id: uuid.UUID,
) -> CallSession | None:
    """Claim a call for extraction by transitioning it under lock."""
    row = await db.execute(
        select(CallSession)
        .where(CallSession.id == call_session_id)
        .with_for_update()
    )
    call_session = row.scalar_one_or_none()
    if call_session is None:
        await db.rollback()
        return None

    if (
        call_session.processing_status
        not in _EXTRACTION_ELIGIBLE_STATUSES
    ):
        logger.info(
            "extraction.skipped",
            call_session_id=str(call_session_id),
            processing_status=call_session.processing_status,
        )
        await db.rollback()
        return None

    call_session.processing_status = "extraction_running"
    await db.commit()
    return call_session


async def _persist_extraction(
    db: AsyncSession,
    call_session_id: uuid.UUID,
    extraction: CallExtraction,
    model_name: str,
    utterances: list[TranscriptUtterance],
) -> ExtractionSnapshot:
    """Persist the extraction snapshot and evidence anchors."""
    utterances_by_sequence = {
        utterance.sequence_number: utterance
        for utterance in utterances
    }
    snapshot = ExtractionSnapshot(
        call_session_id=call_session_id,
        schema_version=SCHEMA_VERSION,
        prompt_version=PROMPT_VERSION,
        model_name=model_name,
        extracted_json=extraction.model_dump(),
        summary=extraction.summary,
        confidence=extraction.confidence,
    )
    db.add(snapshot)
    await db.flush()

    for ev in extraction.evidence:
        matched_utterance = utterances_by_sequence.get(
            ev.sequence_number,
        )
        anchor = EvidenceAnchor(
            call_session_id=call_session_id,
            artifact_type="extraction_snapshot",
            artifact_id=snapshot.id,
            field_name=ev.field,
            transcript_utterance_id=(
                matched_utterance.id
                if matched_utterance is not None
                else None
            ),
            quote_text=ev.quote,
            speaker=ev.speaker,
            sequence_number=ev.sequence_number,
            confidence=extraction.confidence,
        )
        db.add(anchor)

    return snapshot


async def run_extraction(
    db: AsyncSession,
    call_session_id: uuid.UUID,
) -> ExtractionSnapshot | None:
    """Run the full extraction pipeline for a call.

    Transitions ``processing_status``:
      ``transcript_finalized`` → ``extraction_running``
      → ``extraction_completed`` or ``failed_retryable``.

    Returns the snapshot on success, None on failure.
    """
    settings = get_settings()

    # 1. Transition to extraction_running exactly once.
    claimed_session = await _claim_extraction(
        db, call_session_id,
    )
    if claimed_session is None:
        return None

    # 2. Load transcript utterances.
    result = await db.execute(
        select(TranscriptUtterance)
        .where(
            TranscriptUtterance.call_session_id
            == call_session_id,
        )
        .order_by(TranscriptUtterance.sequence_number)
    )
    utterances = list(result.scalars().all())

    if not utterances:
        logger.warning(
            "extraction.no_transcript",
            call_session_id=str(call_session_id),
        )
        await db.execute(
            update(CallSession)
            .where(CallSession.id == call_session_id)
            .values(
                processing_status="failed_retryable",
            )
        )
        await db.commit()
        raise RetryableExtractionError(
            "Transcript not yet available for extraction.",
        )

    transcript_text = _build_transcript_text(utterances)
    model_name = settings.GEMINI_MODEL_EXTRACTION

    # 3. Call Gemini with validation retry.
    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    try:
        extraction = await _call_gemini_with_repair(
            client,
            model_name,
            transcript_text,
            max_retries=settings.LLM_VALIDATION_MAX_RETRIES,
        )
    except ValidationError as exc:
        logger.error(
            "extraction.failed",
            call_session_id=str(call_session_id),
            error=str(exc),
            status="failed_retryable",
        )
        await db.execute(
            update(CallSession)
            .where(CallSession.id == call_session_id)
            .values(processing_status="failed_retryable")
        )
        await db.commit()
        raise RetryableExtractionError(
            "Gemini returned invalid structured output.",
        ) from exc
    except Exception as exc:
        logger.error(
            "extraction.failed",
            call_session_id=str(call_session_id),
            error=str(exc),
            status="failed_terminal",
        )
        await db.execute(
            update(CallSession)
            .where(CallSession.id == call_session_id)
            .values(processing_status="failed_terminal")
        )
        await db.commit()
        return None

    # 4. Persist extraction + evidence anchors.
    try:
        snapshot = await _persist_extraction(
            db,
            call_session_id,
            extraction,
            model_name,
            utterances,
        )

        # 5. Transition to extraction_completed.
        await db.execute(
            update(CallSession)
            .where(CallSession.id == call_session_id)
            .values(processing_status="extraction_completed")
        )
        await db.commit()
    except Exception as exc:
        await db.rollback()
        logger.error(
            "extraction.persistence_failed",
            call_session_id=str(call_session_id),
            error=str(exc),
        )
        await db.execute(
            update(CallSession)
            .where(CallSession.id == call_session_id)
            .values(processing_status="failed_retryable")
        )
        await db.commit()
        raise RetryableExtractionError(
            "Failed to persist extraction artifact.",
        ) from exc

    logger.info(
        "extraction.completed",
        call_session_id=str(call_session_id),
        snapshot_id=str(snapshot.id),
        confidence=extraction.confidence,
    )
    return snapshot
