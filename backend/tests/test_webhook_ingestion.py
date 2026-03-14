"""Tests for webhook ingestion, idempotency, and session projection."""

import uuid

import pytest
from conftest import FakeRedis, FakeResult, FakeSession, load_fixture

from app.models.call_event import CallEvent
from app.models.call_session import CallSession
from app.services.bolna.ingestion import (
    _derive_idempotency_key,
    _normalize_event_type,
    process_bolna_event,
)


def _make_session(
    provider_call_id: str = "exec_xyz789",
) -> CallSession:
    return CallSession(
        id=uuid.uuid4(),
        deal_id=uuid.uuid4(),
        stakeholder_id=uuid.uuid4(),
        provider_name="bolna",
        provider_call_id=provider_call_id,
        status="queued",
        processing_status="pending",
    )


class IngestionSession(FakeSession):
    """Session stub that resolves a call session by
    provider_call_id and tracks update statements."""

    def __init__(
        self,
        call_session: CallSession | None = None,
    ) -> None:
        super().__init__()
        self._call_session = call_session
        self.updates: list[object] = []

    async def execute(self, stmt: object) -> FakeResult:
        # update() statements — track them
        stmt_str = str(type(stmt).__name__)
        if "Update" in stmt_str:
            self.updates.append(stmt)
            return FakeResult(None)
        # select() — return session
        return FakeResult(self._call_session)


# --- Normalization tests ---


def test_status_mapping_completed() -> None:
    assert _normalize_event_type(
        {"status": "completed"},
    ) == "call.completed"


def test_status_mapping_in_progress_hyphenated() -> None:
    assert _normalize_event_type(
        {"status": "in-progress"},
    ) == "call.started"


def test_status_mapping_unknown_returns_none() -> None:
    assert _normalize_event_type(
        {"status": "banana"},
    ) is None


def test_status_mapping_failed_variants() -> None:
    for s in ("failed", "stopped", "error"):
        assert _normalize_event_type(
            {"status": s},
        ) == "call.failed"


# --- Idempotency key tests ---


def test_idempotency_key_prefers_event_id() -> None:
    key = _derive_idempotency_key(
        {"event_id": "evt_123", "status": "completed"},
    )
    assert "evt_123" in key


def test_idempotency_key_fallback_uses_hash() -> None:
    payload = {
        "execution_id": "exec_1",
        "status": "completed",
    }
    key = _derive_idempotency_key(payload)
    assert "exec_1" in key
    assert "completed" in key


# --- Ingestion tests with fixtures ---


@pytest.mark.asyncio
async def test_process_completed_webhook() -> None:
    payload = load_fixture(
        "bolna_webhook_completed.json",
    )
    cs = _make_session("exec_xyz789")
    redis = FakeRedis()
    db = IngestionSession(call_session=cs)

    result = await process_bolna_event(
        db=db,  # type: ignore[arg-type]
        redis=redis,  # type: ignore[arg-type]
        raw_payload=payload,
        source="webhook",
    )

    assert result is True
    events = [
        item for item in db.added
        if isinstance(item, CallEvent)
    ]
    assert len(events) == 1
    assert events[0].event_type == "call.completed"
    # Session projection was updated
    assert len(db.updates) == 1
    assert db.committed is True


@pytest.mark.asyncio
async def test_completed_webhook_enqueues_extraction_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = load_fixture(
        "bolna_webhook_completed.json",
    )
    cs = _make_session("exec_xyz789")
    redis = FakeRedis()
    db = IngestionSession(call_session=cs)
    enqueued: list[str] = []

    async def fake_persist(*_args: object, **_kwargs: object) -> list[object]:
        return [object()]

    monkeypatch.setattr(
        "app.services.bolna.ingestion.persist_transcript",
        fake_persist,
    )
    monkeypatch.setattr(
        "app.services.bolna.ingestion._enqueue_extraction",
        enqueued.append,
    )

    result = await process_bolna_event(
        db=db,  # type: ignore[arg-type]
        redis=redis,  # type: ignore[arg-type]
        raw_payload=payload,
        source="webhook",
    )

    assert result is True
    assert enqueued == [str(cs.id)]


@pytest.mark.asyncio
async def test_completed_webhook_skips_extraction_if_transcript_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = load_fixture(
        "bolna_webhook_completed.json",
    )
    cs = _make_session("exec_xyz789")
    redis = FakeRedis()
    db = IngestionSession(call_session=cs)
    enqueued: list[str] = []

    async def fake_persist(*_args: object, **_kwargs: object) -> list[object]:
        return []

    monkeypatch.setattr(
        "app.services.bolna.ingestion.persist_transcript",
        fake_persist,
    )
    monkeypatch.setattr(
        "app.services.bolna.ingestion._enqueue_extraction",
        enqueued.append,
    )

    result = await process_bolna_event(
        db=db,  # type: ignore[arg-type]
        redis=redis,  # type: ignore[arg-type]
        raw_payload=payload,
        source="webhook",
    )

    assert result is True
    assert enqueued == []


@pytest.mark.asyncio
async def test_duplicate_webhook_is_rejected() -> None:
    """Second delivery of the same event returns False."""
    payload = load_fixture(
        "bolna_webhook_completed.json",
    )
    cs = _make_session("exec_xyz789")
    redis = FakeRedis()
    db = IngestionSession(call_session=cs)

    # First delivery
    first = await process_bolna_event(
        db=db,  # type: ignore[arg-type]
        redis=redis,  # type: ignore[arg-type]
        raw_payload=payload,
        source="webhook",
    )
    assert first is True

    # Second delivery — same payload
    db2 = IngestionSession(call_session=cs)
    second = await process_bolna_event(
        db=db2,  # type: ignore[arg-type]
        redis=redis,  # type: ignore[arg-type]
        raw_payload=payload,
        source="webhook",
    )
    assert second is False
    assert len(db2.added) == 0


@pytest.mark.asyncio
async def test_polling_payload_processed() -> None:
    payload = load_fixture(
        "bolna_execution_polling.json",
    )
    cs = _make_session("exec_xyz789")
    redis = FakeRedis()
    db = IngestionSession(call_session=cs)

    result = await process_bolna_event(
        db=db,  # type: ignore[arg-type]
        redis=redis,  # type: ignore[arg-type]
        raw_payload=payload,
        source="polling",
    )

    assert result is True
    assert db.added[0].event_type == "call.started"


@pytest.mark.asyncio
async def test_unknown_status_persisted_not_projected() -> None:
    """Unknown status is stored as CallEvent but does not
    update the session projection."""
    payload = {
        "execution_id": "exec_xyz789",
        "status": "some_new_status",
    }
    cs = _make_session("exec_xyz789")
    redis = FakeRedis()
    db = IngestionSession(call_session=cs)

    result = await process_bolna_event(
        db=db,  # type: ignore[arg-type]
        redis=redis,  # type: ignore[arg-type]
        raw_payload=payload,
        source="webhook",
    )

    assert result is True
    event = db.added[0]
    assert event.event_type == "unknown.some_new_status"
    # No session projection update for unknown statuses
    assert len(db.updates) == 0


@pytest.mark.asyncio
async def test_no_session_returns_false() -> None:
    payload = {
        "execution_id": "nonexistent",
        "status": "completed",
    }
    redis = FakeRedis()
    db = IngestionSession(call_session=None)

    result = await process_bolna_event(
        db=db,  # type: ignore[arg-type]
        redis=redis,  # type: ignore[arg-type]
        raw_payload=payload,
        source="webhook",
    )

    assert result is False
    # Idempotency key must be released so retries
    # succeed once the session row appears.
    idem_key = _derive_idempotency_key(payload)
    assert await redis.get(idem_key) is None


@pytest.mark.asyncio
async def test_db_failure_releases_idempotency_key() -> None:
    """If the DB write fails, the idempotency key must
    be released so the provider retry is not blocked."""

    class FailingSession(IngestionSession):
        async def flush(self) -> None:
            raise RuntimeError("simulated DB error")

    payload = load_fixture(
        "bolna_webhook_completed.json",
    )
    cs = _make_session("exec_xyz789")
    redis = FakeRedis()
    db = FailingSession(call_session=cs)

    with pytest.raises(RuntimeError, match="simulated"):
        await process_bolna_event(
            db=db,  # type: ignore[arg-type]
            redis=redis,  # type: ignore[arg-type]
            raw_payload=payload,
            source="webhook",
        )

    idem_key = _derive_idempotency_key(payload)
    assert await redis.get(idem_key) is None
