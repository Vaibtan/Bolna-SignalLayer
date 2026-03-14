"""Tests for memory document generation service."""

import uuid
from datetime import datetime, timezone
from typing import Any

import pytest
from conftest import FakeScalarsResult
from sqlalchemy.exc import IntegrityError

from app.models.call_session import CallSession
from app.models.deal import Deal
from app.models.extraction_snapshot import ExtractionSnapshot
from app.models.memory_document import MemoryDocument
from app.models.risk_snapshot import RiskSnapshot
from app.models.stakeholder import Stakeholder
from app.services.memory.service import (
    _build_documents,
    generate_memory_documents,
)


def _make_deal() -> Deal:
    d = Deal(
        id=uuid.uuid4(),
        org_id=uuid.uuid4(),
        name="Test Deal",
        account_name="Acme",
        stage="discovery",
    )
    d.created_at = datetime.now(timezone.utc)
    d.updated_at = datetime.now(timezone.utc)
    return d


def _make_extraction(
    call_session_id: uuid.UUID,
) -> ExtractionSnapshot:
    return ExtractionSnapshot(
        id=uuid.uuid4(),
        call_session_id=call_session_id,
        schema_version="1.0",
        prompt_version="1.0",
        model_name="gemini-2.5-flash",
        extracted_json={
            "stakeholder": {
                "name": "Jane",
                "title": "VP Eng",
                "role_label": "champion",
            },
            "deal_signals": {
                "objections": ["price too high"],
                "next_step": "Send proposal",
            },
            "interaction": {
                "sentiment": "positive",
            },
        },
        summary="Good call with Jane about Q2 plans.",
        confidence=0.85,
        created_at=datetime.now(timezone.utc),
    )


def _make_risk(deal_id: uuid.UUID) -> RiskSnapshot:
    return RiskSnapshot(
        id=uuid.uuid4(),
        deal_id=deal_id,
        score=35,
        level="medium",
        factors_json={
            "factors": ["No economic buyer identified"],
        },
        created_at=datetime.now(timezone.utc),
    )


def _make_stakeholder(deal_id: uuid.UUID) -> Stakeholder:
    sh = Stakeholder(
        id=uuid.uuid4(),
        deal_id=deal_id,
        name="Jane Doe",
        source_type="manual",
    )
    sh.created_at = datetime.now(timezone.utc)
    sh.updated_at = datetime.now(timezone.utc)
    return sh


# --- Document building tests ---


def test_build_documents_creates_all_types() -> None:
    deal = _make_deal()
    call_id = uuid.uuid4()
    ext = _make_extraction(call_id)
    risk = _make_risk(deal.id)
    sh = _make_stakeholder(deal.id)

    docs = _build_documents(deal, ext, risk, sh, call_id)

    types = {d["doc_type"] for d in docs}
    assert "call_summary" in types
    assert "objection_summary" in types
    assert "stakeholder_profile_summary" in types
    assert "deal_state_summary" in types
    assert "action_rationale_summary" in types
    assert len(docs) == 5


def test_build_documents_without_objections() -> None:
    deal = _make_deal()
    call_id = uuid.uuid4()
    ext = _make_extraction(call_id)
    ext.extracted_json = {
        **dict(ext.extracted_json),
        "deal_signals": {
            "objections": [],
            "next_step": "Follow up",
        },
    }
    risk = _make_risk(deal.id)
    sh = _make_stakeholder(deal.id)

    docs = _build_documents(deal, ext, risk, sh, call_id)

    types = {d["doc_type"] for d in docs}
    assert "objection_summary" not in types


def test_build_documents_without_risk() -> None:
    deal = _make_deal()
    call_id = uuid.uuid4()
    ext = _make_extraction(call_id)
    sh = _make_stakeholder(deal.id)

    docs = _build_documents(deal, ext, None, sh, call_id)

    types = {d["doc_type"] for d in docs}
    assert "action_rationale_summary" not in types
    assert "deal_state_summary" in types


def test_build_documents_all_have_deal_id() -> None:
    deal = _make_deal()
    call_id = uuid.uuid4()
    ext = _make_extraction(call_id)
    risk = _make_risk(deal.id)

    docs = _build_documents(deal, ext, risk, None, call_id)

    for doc in docs:
        assert doc["deal_id"] == deal.id
        assert doc["call_session_id"] == call_id


# --- Service integration tests ---


class MemorySession:
    """Fake DB session for memory tests."""

    def __init__(
        self,
        call_session: CallSession | None = None,
        deal: Deal | None = None,
        extraction: ExtractionSnapshot | None = None,
        risk: RiskSnapshot | None = None,
        stakeholder: Stakeholder | None = None,
        *,
        has_existing: bool = False,
        raise_integrity_on_commit: bool = False,
    ) -> None:
        # First response: idempotency check (existing docs).
        idem_val: Any = (
            uuid.uuid4() if has_existing else None
        )
        self._responses: list[Any] = [
            idem_val,
            call_session,
            deal,
            extraction,
            risk,
            stakeholder,
        ]
        self._idx = 0
        self.added: list[Any] = []
        self.committed = 0
        self.raise_integrity_on_commit = (
            raise_integrity_on_commit
        )

    async def execute(self, _stmt: object) -> Any:
        idx = self._idx
        self._idx += 1
        val = (
            self._responses[idx]
            if idx < len(self._responses)
            else None
        )
        if isinstance(val, list):
            return FakeScalarsResult(val)
        from conftest import FakeResult
        return FakeResult(val)

    def add(self, instance: Any) -> None:
        self.added.append(instance)

    async def commit(self) -> None:
        if self.raise_integrity_on_commit:
            raise IntegrityError(
                "duplicate",
                params={},
                orig=Exception("duplicate"),
            )
        self.committed += 1

    async def rollback(self) -> None:
        pass


@pytest.mark.asyncio
async def test_generate_memory_documents_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deal = _make_deal()
    sh = _make_stakeholder(deal.id)
    call_id = uuid.uuid4()
    cs = CallSession(
        id=call_id,
        deal_id=deal.id,
        stakeholder_id=sh.id,
        provider_name="bolna",
        status="completed",
        processing_status="recommendation_completed",
    )
    cs.created_at = datetime.now(timezone.utc)
    cs.updated_at = datetime.now(timezone.utc)

    ext = _make_extraction(call_id)
    risk = _make_risk(deal.id)

    db = MemorySession(
        call_session=cs,
        deal=deal,
        extraction=ext,
        risk=risk,
        stakeholder=sh,
    )

    from unittest.mock import MagicMock

    fake_settings = MagicMock()
    fake_settings.GEMINI_API_KEY = "test-key"
    fake_settings.GEMINI_MODEL_EMBEDDING = "embedding-001"
    monkeypatch.setattr(
        "app.services.memory.service.get_settings",
        lambda: fake_settings,
    )

    fake_embedding_result = MagicMock()
    fake_embedding_value = MagicMock()
    fake_embedding_value.values = [0.1] * 3072
    fake_embedding_result.embeddings = [fake_embedding_value]

    fake_client = MagicMock()
    fake_client.models.embed_content.return_value = (
        fake_embedding_result
    )
    monkeypatch.setattr(
        "app.services.memory.service.genai.Client",
        lambda api_key: fake_client,
    )

    docs = await generate_memory_documents(
        db, call_id,  # type: ignore[arg-type]
    )

    assert len(docs) >= 4
    assert db.committed == 1
    assert all(isinstance(d, MemoryDocument) for d in docs)

    mem_docs = [
        a for a in db.added
        if isinstance(a, MemoryDocument)
    ]
    assert len(mem_docs) >= 4
    assert all(d.embedding is not None for d in mem_docs)


@pytest.mark.asyncio
async def test_generate_memory_documents_no_session() -> None:
    db = MemorySession()

    docs = await generate_memory_documents(
        db, uuid.uuid4(),  # type: ignore[arg-type]
    )

    assert docs == []


@pytest.mark.asyncio
async def test_generate_memory_documents_idempotent() -> None:
    """Second call for same session returns empty."""
    db = MemorySession(has_existing=True)

    docs = await generate_memory_documents(
        db, uuid.uuid4(),  # type: ignore[arg-type]
    )

    assert docs == []
    assert db.committed == 0


@pytest.mark.asyncio
async def test_generate_memory_documents_duplicate_commit_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deal = _make_deal()
    sh = _make_stakeholder(deal.id)
    call_id = uuid.uuid4()
    cs = CallSession(
        id=call_id,
        deal_id=deal.id,
        stakeholder_id=sh.id,
        provider_name="bolna",
        status="completed",
        processing_status="recommendation_completed",
    )
    cs.created_at = datetime.now(timezone.utc)
    cs.updated_at = datetime.now(timezone.utc)

    ext = _make_extraction(call_id)
    risk = _make_risk(deal.id)

    db = MemorySession(
        call_session=cs,
        deal=deal,
        extraction=ext,
        risk=risk,
        stakeholder=sh,
        raise_integrity_on_commit=True,
    )

    from unittest.mock import MagicMock

    fake_settings = MagicMock()
    fake_settings.GEMINI_API_KEY = "test-key"
    fake_settings.GEMINI_MODEL_EMBEDDING = "embedding-001"
    monkeypatch.setattr(
        "app.services.memory.service.get_settings",
        lambda: fake_settings,
    )

    fake_embedding_result = MagicMock()
    fake_embedding_value = MagicMock()
    fake_embedding_value.values = [0.1] * 3072
    fake_embedding_result.embeddings = [fake_embedding_value]

    fake_client = MagicMock()
    fake_client.models.embed_content.return_value = (
        fake_embedding_result
    )
    monkeypatch.setattr(
        "app.services.memory.service.genai.Client",
        lambda api_key: fake_client,
    )

    docs = await generate_memory_documents(
        db, call_id,  # type: ignore[arg-type]
    )

    assert docs == []
