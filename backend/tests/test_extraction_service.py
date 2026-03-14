"""Tests for the extraction pipeline service."""

import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest
from conftest import FakeScalarsResult
from pydantic import ValidationError

from app.models.evidence_anchor import EvidenceAnchor
from app.models.extraction_snapshot import ExtractionSnapshot
from app.models.transcript_utterance import TranscriptUtterance
from app.services.extraction.schema import (
    PROMPT_VERSION,
    SCHEMA_VERSION,
    CallExtraction,
    DealSignalsExtraction,
    EvidenceItem,
    InteractionExtraction,
    QualificationExtraction,
    StakeholderExtraction,
)
from app.services.extraction.service import (
    RetryableExtractionError,
    _build_transcript_text,
    _persist_extraction,
    run_extraction,
)


def _sample_extraction() -> CallExtraction:
    """Build a minimal valid extraction."""
    return CallExtraction(
        stakeholder=StakeholderExtraction(
            name="Jane Doe",
            title="VP Engineering",
            role_label="champion",
            role_confidence=0.85,
        ),
        qualification=QualificationExtraction(
            budget_signal="positive",
            authority_signal="unknown",
            need_signal="positive",
            timeline_signal="positive",
        ),
        deal_signals=DealSignalsExtraction(
            pain_points=["slow onboarding"],
            next_step="Send proposal by Friday",
            timeline_detail="Q2 procurement",
            budget_detail="Budget allocated",
        ),
        interaction=InteractionExtraction(
            sentiment="positive",
            engagement_level="high",
            followup_requested=True,
        ),
        evidence=[
            EvidenceItem(
                field="next_step",
                quote="Send the proposal by Friday.",
                speaker="prospect",
                sequence_number=3,
            ),
        ],
        summary="Productive call with Jane Doe.",
        confidence=0.82,
    )


def _make_utterances(
    call_session_id: uuid.UUID,
) -> list[TranscriptUtterance]:
    """Build sample utterances for tests."""
    utts = []
    texts = [
        ("agent", "Hello, how are you?"),
        ("prospect", "Good, thanks for calling."),
        ("agent", "I wanted to discuss the deal."),
        (
            "prospect",
            "Send the proposal by Friday.",
        ),
    ]
    for seq, (speaker, text) in enumerate(texts):
        u = TranscriptUtterance(
            id=uuid.uuid4(),
            call_session_id=call_session_id,
            speaker=speaker,
            text=text,
            sequence_number=seq,
            is_final=True,
        )
        utts.append(u)
    return utts


# --- Schema tests ---


def test_schema_validates_valid_extraction() -> None:
    ext = _sample_extraction()
    assert ext.confidence == 0.82
    assert ext.stakeholder.role_label == "champion"
    assert len(ext.evidence) == 1


def test_schema_rejects_missing_required() -> None:
    with pytest.raises(ValidationError):
        CallExtraction(
            stakeholder=StakeholderExtraction(
                name="X",
                title="Y",
                role_label="unknown",
                role_confidence=0.0,
            ),
            # Missing qualification, deal_signals, etc.
        )  # type: ignore[call-arg]


def test_schema_version_constants() -> None:
    assert SCHEMA_VERSION == "1.0"
    assert PROMPT_VERSION == "1.0"


# --- Transcript formatting ---


def test_build_transcript_text() -> None:
    utts = _make_utterances(uuid.uuid4())
    text = _build_transcript_text(utts)
    lines = text.strip().split("\n")
    assert len(lines) == 4
    assert lines[0].startswith("[0] Agent:")
    assert lines[1].startswith("[1] Prospect:")


# --- Persistence tests ---


class ExtractionSession:
    """Fake DB session for extraction persistence."""

    def __init__(
        self,
        utterances: list[TranscriptUtterance] | None = None,
        *,
        processing_status: str = "transcript_finalized",
    ) -> None:
        self._utterances = utterances or []
        self.call_session = MagicMock()
        self.call_session.id = uuid.uuid4()
        self.call_session.processing_status = processing_status
        self.added: list[Any] = []
        self.updates: list[dict[str, Any]] = []
        self.committed = 0
        self.rolled_back = 0
        self._execute_count = 0

    async def execute(self, stmt: object) -> Any:
        self._execute_count += 1
        stmt_str = str(stmt)
        if "FROM call_sessions" in stmt_str:
            return FakeScalarsResult([self.call_session])
        if "UPDATE" in stmt_str:
            values = getattr(stmt, "_values", {})
            processing_status = values.get("processing_status")
            if processing_status is not None:
                self.call_session.processing_status = getattr(
                    processing_status, "value", processing_status,
                )
            return None
        if "FROM transcript_utterances" in stmt_str:
            if self._utterances:
                return FakeScalarsResult(self._utterances)
            return FakeScalarsResult([])
        if self._utterances:
            return FakeScalarsResult(self._utterances)
        return FakeScalarsResult([])

    def add(self, instance: Any) -> None:
        self.added.append(instance)

    async def flush(self) -> None:
        for item in self.added:
            if not hasattr(item, "id") or item.id is None:
                item.id = uuid.uuid4()

    async def commit(self) -> None:
        self.committed += 1

    async def rollback(self) -> None:
        self.rolled_back += 1


@pytest.mark.asyncio
async def test_persist_extraction_creates_snapshot_and_anchors() -> None:
    db = ExtractionSession()
    call_id = uuid.uuid4()
    extraction = _sample_extraction()
    utterances = _make_utterances(call_id)

    snapshot = await _persist_extraction(
        db,  # type: ignore[arg-type]
        call_id,
        extraction,
        "gemini-2.5-flash",
        utterances,
    )

    assert isinstance(snapshot, ExtractionSnapshot)
    assert snapshot.schema_version == SCHEMA_VERSION
    assert snapshot.model_name == "gemini-2.5-flash"
    assert snapshot.summary == extraction.summary

    snapshots = [
        a
        for a in db.added
        if isinstance(a, ExtractionSnapshot)
    ]
    anchors = [
        a
        for a in db.added
        if isinstance(a, EvidenceAnchor)
    ]
    assert len(snapshots) == 1
    assert len(anchors) == 1
    assert anchors[0].field_name == "next_step"
    assert anchors[0].artifact_type == "extraction_snapshot"
    assert anchors[0].transcript_utterance_id == utterances[3].id
    assert anchors[0].confidence == extraction.confidence


# --- run_extraction integration tests ---


@pytest.mark.asyncio
async def test_run_extraction_no_utterances(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Extraction with no transcript → failed_retryable."""
    db = ExtractionSession(utterances=[])
    call_id = uuid.uuid4()

    with pytest.raises(RetryableExtractionError):
        await run_extraction(
            db,  # type: ignore[arg-type]
            call_id,
        )

    assert db.committed >= 2  # extraction_running + failed


@pytest.mark.asyncio
async def test_run_extraction_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Extraction with valid Gemini response succeeds."""
    call_id = uuid.uuid4()
    utts = _make_utterances(call_id)
    db = ExtractionSession(utterances=utts)

    extraction = _sample_extraction()

    # Mock get_settings
    fake_settings = MagicMock()
    fake_settings.GEMINI_API_KEY = "test-key"
    fake_settings.GEMINI_MODEL_EXTRACTION = "gemini-test"
    fake_settings.LLM_VALIDATION_MAX_RETRIES = 1
    monkeypatch.setattr(
        "app.services.extraction.service.get_settings",
        lambda: fake_settings,
    )

    # Mock Gemini client
    fake_response = MagicMock()
    fake_response.text = extraction.model_dump_json()

    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = (
        fake_response
    )
    monkeypatch.setattr(
        "app.services.extraction.service.genai.Client",
        lambda api_key: fake_client,
    )

    result = await run_extraction(
        db,  # type: ignore[arg-type]
        call_id,
    )

    assert result is not None
    assert isinstance(result, ExtractionSnapshot)
    assert result.summary == extraction.summary
    assert db.committed >= 2  # extraction_running + completed

    snapshots = [
        a
        for a in db.added
        if isinstance(a, ExtractionSnapshot)
    ]
    assert len(snapshots) == 1


@pytest.mark.asyncio
async def test_run_extraction_validation_failure_is_retryable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validation failure after repair attempts → failed_retryable."""
    call_id = uuid.uuid4()
    utts = _make_utterances(call_id)
    db = ExtractionSession(utterances=utts)

    fake_settings = MagicMock()
    fake_settings.GEMINI_API_KEY = "test-key"
    fake_settings.GEMINI_MODEL_EXTRACTION = "gemini-test"
    fake_settings.LLM_VALIDATION_MAX_RETRIES = 1
    monkeypatch.setattr(
        "app.services.extraction.service.get_settings",
        lambda: fake_settings,
    )

    invalid_response = MagicMock()
    invalid_response.text = '{"summary":"missing most fields"}'

    fake_client = MagicMock()
    fake_client.models.generate_content.side_effect = [
        invalid_response,
        invalid_response,
    ]
    monkeypatch.setattr(
        "app.services.extraction.service.genai.Client",
        lambda api_key: fake_client,
    )

    with pytest.raises(RetryableExtractionError):
        await run_extraction(
            db,  # type: ignore[arg-type]
            call_id,
        )

    assert db.committed >= 2
    assert fake_client.models.generate_content.call_count == 2
    second_prompt = fake_client.models.generate_content.call_args_list[
        1
    ].kwargs["contents"]
    assert "failed validation" in second_prompt


@pytest.mark.asyncio
async def test_run_extraction_gemini_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Gemini API error → failed_terminal."""
    call_id = uuid.uuid4()
    utts = _make_utterances(call_id)
    db = ExtractionSession(utterances=utts)

    fake_settings = MagicMock()
    fake_settings.GEMINI_API_KEY = "test-key"
    fake_settings.GEMINI_MODEL_EXTRACTION = "gemini-test"
    fake_settings.LLM_VALIDATION_MAX_RETRIES = 0
    monkeypatch.setattr(
        "app.services.extraction.service.get_settings",
        lambda: fake_settings,
    )

    fake_client = MagicMock()
    fake_client.models.generate_content.side_effect = (
        RuntimeError("API down")
    )
    monkeypatch.setattr(
        "app.services.extraction.service.genai.Client",
        lambda api_key: fake_client,
    )

    result = await run_extraction(
        db,  # type: ignore[arg-type]
        call_id,
    )

    assert result is None
    # Should be 2 commits: extraction_running + failed_terminal
    assert db.committed >= 2


@pytest.mark.asyncio
async def test_run_extraction_skips_when_already_running() -> None:
    """Duplicate workers must not re-run extraction for a call."""
    call_id = uuid.uuid4()
    utts = _make_utterances(call_id)
    db = ExtractionSession(
        utterances=utts,
        processing_status="extraction_running",
    )

    result = await run_extraction(
        db,  # type: ignore[arg-type]
        call_id,
    )

    assert result is None
    assert db.committed == 0
