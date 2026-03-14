"""Transcript normalization service.

Converts provider-delivered transcript text into durable
``TranscriptUtterance`` rows.  Bolna delivers a flat string
on terminal payloads, so the normalizer does best-effort
speaker-turn splitting and falls back to a single utterance
when the text has no recognizable speaker prefixes.
"""

from __future__ import annotations

import re
import uuid

import structlog
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transcript_utterance import TranscriptUtterance

logger = structlog.get_logger(__name__)

# Matches lines starting with a speaker label, e.g.
# "Agent: Hello" or "User: Hi there" or "Prospect: Yes".
_SPEAKER_RE = re.compile(
    r"^(Agent|AI|Assistant|Bot|User|Prospect|Customer|Human)\s*:\s*",
    re.IGNORECASE | re.MULTILINE,
)


def _parse_turns(transcript: str) -> list[tuple[str, str]]:
    """Split a transcript string into (speaker, text) turns.

    If no speaker prefixes are found, the entire text is
    returned as a single turn with speaker ``"unknown"``.
    """
    splits = _SPEAKER_RE.split(transcript)

    # If no speaker labels matched, splits has a single element.
    if len(splits) <= 1:
        cleaned = transcript.strip()
        if not cleaned:
            return []
        return [("unknown", cleaned)]

    turns: list[tuple[str, str]] = []
    # _SPEAKER_RE has one capture group, so splits alternates:
    # [pre-text, speaker1, text1, speaker2, text2, ...]
    # Index 0 is text before the first speaker label (usually empty).
    i = 1
    while i < len(splits) - 1:
        speaker = _normalize_speaker(splits[i])
        text = splits[i + 1].strip()
        if text:
            turns.append((speaker, text))
        i += 2

    # If the regex consumed nothing useful, fall back.
    if not turns:
        cleaned = transcript.strip()
        if cleaned:
            return [("unknown", cleaned)]
    return turns


def _normalize_speaker(raw: str) -> str:
    """Canonicalize speaker labels to ``agent`` or ``prospect``."""
    lower = raw.strip().lower()
    if lower in {"agent", "ai", "assistant", "bot"}:
        return "agent"
    if lower in {"user", "prospect", "customer", "human"}:
        return "prospect"
    return lower


async def persist_transcript(
    db: AsyncSession,
    call_session_id: uuid.UUID,
    transcript: str,
) -> list[TranscriptUtterance]:
    """Parse and persist transcript utterances.

    Idempotent — if utterances already exist for this call
    session, returns an empty list and does nothing.

    Returns the newly created utterance rows (empty if
    already persisted or transcript is blank).
    """
    if not transcript or not transcript.strip():
        return []

    turns = _parse_turns(transcript)
    if not turns:
        return []

    utterances: list[TranscriptUtterance] = []
    try:
        async with db.begin_nested():
            for seq, (speaker, text) in enumerate(turns):
                utt = TranscriptUtterance(
                    call_session_id=call_session_id,
                    speaker=speaker,
                    text=text,
                    sequence_number=seq,
                    is_final=True,
                )
                db.add(utt)
                utterances.append(utt)

            await db.flush()
    except IntegrityError:
        logger.debug(
            "transcript.already_persisted",
            call_session_id=str(call_session_id),
        )
        return []

    logger.info(
        "transcript.persisted",
        call_session_id=str(call_session_id),
        utterance_count=len(utterances),
    )
    return utterances
