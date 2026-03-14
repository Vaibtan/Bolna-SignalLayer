"""Tests for transcript normalization service."""

import uuid
from typing import Any

import pytest
from conftest import FakeResult
from sqlalchemy.exc import IntegrityError

from app.models.transcript_utterance import TranscriptUtterance
from app.services.transcripts.service import (
    _normalize_speaker,
    _parse_turns,
    persist_transcript,
)


class TranscriptSession:
    """Fake DB session for transcript persistence tests."""

    def __init__(
        self,
        *,
        duplicate_on_flush: bool = False,
    ) -> None:
        self._duplicate_on_flush = duplicate_on_flush
        self.added: list[Any] = []
        self.flushed = False

    async def execute(self, _stmt: object) -> FakeResult:
        return FakeResult(None)

    def add(self, instance: Any) -> None:
        self.added.append(instance)

    async def __aenter__(self) -> 'TranscriptSession':
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    def begin_nested(self) -> 'TranscriptSession':
        return self

    async def flush(self) -> None:
        if self._duplicate_on_flush:
            raise IntegrityError(
                "duplicate transcript",
                params=None,
                orig=Exception("duplicate"),
            )
        self.flushed = True


# --- Unit tests for parsing ---


def test_parse_turns_with_speaker_labels() -> None:
    transcript = (
        "Agent: Hello, how are you today?\n"
        "User: I'm good, thanks for calling.\n"
        "Agent: Great, I wanted to discuss the deal."
    )
    turns = _parse_turns(transcript)
    assert len(turns) == 3
    assert turns[0] == ("agent", "Hello, how are you today?")
    assert turns[1] == ("prospect", "I'm good, thanks for calling.")
    assert turns[2] == ("agent", "Great, I wanted to discuss the deal.")


def test_parse_turns_flat_string_no_labels() -> None:
    transcript = (
        "Hello, this is Jane from Acme Corp."
        " We need to discuss the timeline."
    )
    turns = _parse_turns(transcript)
    assert len(turns) == 1
    assert turns[0][0] == "unknown"
    assert "Jane from Acme Corp" in turns[0][1]


def test_parse_turns_empty_string() -> None:
    assert _parse_turns("") == []
    assert _parse_turns("   ") == []


def test_parse_turns_mixed_case_labels() -> None:
    transcript = "AGENT: Hi\nPROSPECT: Hello"
    turns = _parse_turns(transcript)
    assert len(turns) == 2
    assert turns[0][0] == "agent"
    assert turns[1][0] == "prospect"


def test_parse_turns_ai_and_customer_labels() -> None:
    transcript = "AI: Welcome.\nCustomer: Thanks."
    turns = _parse_turns(transcript)
    assert len(turns) == 2
    assert turns[0][0] == "agent"
    assert turns[1][0] == "prospect"


def test_normalize_speaker_mapping() -> None:
    assert _normalize_speaker("Agent") == "agent"
    assert _normalize_speaker("AI") == "agent"
    assert _normalize_speaker("Bot") == "agent"
    assert _normalize_speaker("Assistant") == "agent"
    assert _normalize_speaker("User") == "prospect"
    assert _normalize_speaker("Prospect") == "prospect"
    assert _normalize_speaker("Customer") == "prospect"
    assert _normalize_speaker("Human") == "prospect"


# --- Integration tests for persist_transcript ---


@pytest.mark.asyncio
async def test_persist_transcript_creates_utterances() -> None:
    db = TranscriptSession()
    call_id = uuid.uuid4()
    transcript = "Agent: Hello.\nUser: Hi there."

    result = await persist_transcript(  # type: ignore[arg-type]
        db, call_id, transcript,
    )

    assert len(result) == 2
    assert db.flushed
    assert len(db.added) == 2
    assert all(isinstance(u, TranscriptUtterance) for u in db.added)
    assert db.added[0].speaker == "agent"
    assert db.added[0].sequence_number == 0
    assert db.added[1].speaker == "prospect"
    assert db.added[1].sequence_number == 1


@pytest.mark.asyncio
async def test_persist_transcript_flat_string() -> None:
    db = TranscriptSession()
    call_id = uuid.uuid4()

    result = await persist_transcript(  # type: ignore[arg-type]
        db, call_id, "A plain transcript.",
    )

    assert len(result) == 1
    assert result[0].speaker == "unknown"
    assert result[0].text == "A plain transcript."
    assert result[0].is_final is True


@pytest.mark.asyncio
async def test_persist_transcript_idempotent() -> None:
    db = TranscriptSession(duplicate_on_flush=True)
    call_id = uuid.uuid4()

    result = await persist_transcript(  # type: ignore[arg-type]
        db, call_id, "Agent: Hi.",
    )

    assert result == []
    assert db.flushed is False


@pytest.mark.asyncio
async def test_persist_transcript_blank() -> None:
    db = TranscriptSession()
    result = await persist_transcript(  # type: ignore[arg-type]
        db, uuid.uuid4(), "",
    )
    assert result == []

    result = await persist_transcript(  # type: ignore[arg-type]
        db, uuid.uuid4(), "   ",
    )
    assert result == []
