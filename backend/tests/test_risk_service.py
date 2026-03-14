"""Tests for the risk engine."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from conftest import FakeScalarsResult

from app.models.call_session import CallSession
from app.models.deal import Deal
from app.models.deal_snapshot import DealSnapshot
from app.models.extraction_snapshot import ExtractionSnapshot
from app.models.risk_snapshot import RiskSnapshot
from app.models.stakeholder import Stakeholder
from app.models.stakeholder_snapshot import StakeholderSnapshot
from app.services.risk.scoring import risk_level, score_extraction
from app.services.risk.service import (
    RetryableRiskError,
    run_risk_update,
)


def _extraction_data(**overrides: Any) -> dict[str, Any]:
    """Build a minimal extraction dict with overrides."""
    base: dict[str, Any] = {
        "stakeholder": {
            "name": "Jane",
            "title": "VP Eng",
            "role_label": "unknown",
            "role_confidence": 0.5,
        },
        "qualification": {
            "budget_signal": "unknown",
            "authority_signal": "unknown",
            "need_signal": "positive",
            "timeline_signal": "unknown",
        },
        "deal_signals": {
            "pain_points": [],
            "objections": [],
            "competitors": [],
            "security_mentions": [],
            "procurement_mentions": [],
            "next_step": "",
            "timeline_detail": "",
            "budget_detail": "",
        },
        "interaction": {
            "sentiment": "neutral",
            "engagement_level": "medium",
            "followup_requested": False,
        },
        "evidence": [],
        "summary": "Test call.",
        "confidence": 0.7,
    }
    for k, v in overrides.items():
        parts = k.split(".")
        target = base
        for part in parts[:-1]:
            target = target[part]
        target[parts[-1]] = v
    return base


# --- Deterministic scoring tests ---


def test_clean_deal_low_risk() -> None:
    data = _extraction_data(
        **{
            "stakeholder.role_label": "economic_buyer",
            "deal_signals.next_step": "Send proposal",
            "qualification.budget_signal": "positive",
        },
    )
    score, factors = score_extraction(data, 3)
    assert score <= 25
    assert risk_level(score) == "low"
    assert "No committed next step" not in factors
    assert "No economic buyer identified" not in factors


def test_no_next_step_adds_risk() -> None:
    data = _extraction_data(
        **{"stakeholder.role_label": "economic_buyer"},
    )
    score, factors = score_extraction(data, 3)
    assert "No committed next step" in factors


def test_no_economic_buyer_adds_risk() -> None:
    data = _extraction_data(
        **{"deal_signals.next_step": "Follow up"},
    )
    score, factors = score_extraction(data, 3)
    assert "No economic buyer identified" in factors


def test_single_threaded_account() -> None:
    data = _extraction_data()
    score, factors = score_extraction(data, 1)
    assert "Single-threaded account" in factors

    _, factors2 = score_extraction(data, 3)
    assert "Single-threaded account" not in factors2


def test_negative_sentiment() -> None:
    data = _extraction_data(
        **{"interaction.sentiment": "negative"},
    )
    _, factors = score_extraction(data, 3)
    assert "Negative sentiment detected" in factors


def test_security_blocker() -> None:
    data = _extraction_data(
        **{
            "deal_signals.security_mentions": [
                "SOC2 required",
            ],
        },
    )
    _, factors = score_extraction(data, 3)
    assert (
        "Security or compliance blocker raised" in factors
    )


def test_objections_capped() -> None:
    data = _extraction_data(
        **{
            "deal_signals.objections": [
                "price",
                "timing",
                "scope",
                "support",
            ],
        },
    )
    score, factors = score_extraction(data, 3)
    assert "4 unresolved objection(s)" in factors


def test_score_capped_at_100() -> None:
    """Even with all factors active, score never exceeds 100."""
    data = _extraction_data(
        **{
            "deal_signals.next_step": "",
            "deal_signals.objections": ["a", "b", "c"],
            "deal_signals.security_mentions": ["SOC2"],
            "deal_signals.procurement_mentions": ["RFP"],
            "interaction.sentiment": "negative",
            "interaction.engagement_level": "low",
            "qualification.budget_signal": "negative",
            "qualification.authority_signal": "negative",
            "qualification.timeline_signal": "negative",
        },
    )
    score, _ = score_extraction(data, 1)
    assert score <= 100


def test_risk_level_thresholds() -> None:
    assert risk_level(0) == "low"
    assert risk_level(25) == "low"
    assert risk_level(26) == "medium"
    assert risk_level(50) == "medium"
    assert risk_level(51) == "high"
    assert risk_level(75) == "high"
    assert risk_level(76) == "critical"
    assert risk_level(100) == "critical"


# --- Service integration tests ---


class _FakeUpdateResult:
    """Stub for UPDATE statement results."""


class RiskSession:
    """Fake DB session for risk service tests.

    SELECT queries are served from a queue in order.
    UPDATE queries return a no-op result.
    """

    def __init__(
        self,
        call_session: CallSession | None = None,
        deal: Deal | None = None,
        extraction: ExtractionSnapshot | None = None,
        stakeholders: list[Stakeholder] | None = None,
        prev_risk: RiskSnapshot | None = None,
    ) -> None:
        self._select_responses: list[Any] = [
            call_session,
            deal,
            extraction,
            stakeholders or [],
            prev_risk,
        ]
        self._select_idx = 0
        self.added: list[Any] = []
        self.committed = 0

    async def execute(self, stmt: object) -> Any:
        from sqlalchemy.sql.dml import UpdateBase

        if isinstance(stmt, UpdateBase):
            return _FakeUpdateResult()

        idx = self._select_idx
        self._select_idx += 1
        val = (
            self._select_responses[idx]
            if idx < len(self._select_responses)
            else None
        )
        if isinstance(val, list):
            return FakeScalarsResult(val)
        from conftest import FakeResult
        return FakeResult(val)

    def add(self, instance: Any) -> None:
        self.added.append(instance)

    async def flush(self) -> None:
        for item in self.added:
            if not hasattr(item, "id") or item.id is None:
                item.id = uuid.uuid4()

    async def commit(self) -> None:
        self.committed += 1

    async def rollback(self) -> None:
        pass


def _make_call_session(
    deal_id: uuid.UUID,
    stakeholder_id: uuid.UUID,
) -> CallSession:
    cs = CallSession(
        id=uuid.uuid4(),
        deal_id=deal_id,
        stakeholder_id=stakeholder_id,
        provider_name="bolna",
        status="completed",
        processing_status="extraction_completed",
        objective="discovery_qualification",
    )
    cs.created_at = datetime.now(timezone.utc)
    cs.updated_at = datetime.now(timezone.utc)
    return cs


def _make_deal(org_id: uuid.UUID) -> Deal:
    d = Deal(
        id=uuid.uuid4(),
        org_id=org_id,
        name="Test Deal",
        account_name="Acme",
        stage="discovery",
    )
    d.created_at = datetime.now(timezone.utc)
    d.updated_at = datetime.now(timezone.utc)
    return d


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


def _make_extraction(
    call_session_id: uuid.UUID,
) -> ExtractionSnapshot:
    ext = ExtractionSnapshot(
        id=uuid.uuid4(),
        call_session_id=call_session_id,
        schema_version="1.0",
        prompt_version="1.0",
        model_name="gemini-2.5-flash",
        extracted_json=_extraction_data(
            **{
                "stakeholder.role_label": "champion",
                "deal_signals.next_step": "Follow up Friday",
            },
        ),
        summary="Good discovery call.",
        confidence=0.85,
    )
    ext.created_at = datetime.now(timezone.utc)
    return ext


@pytest.mark.asyncio
async def test_run_risk_update_success() -> None:
    org_id = uuid.uuid4()
    deal = _make_deal(org_id)
    sh = _make_stakeholder(deal.id)
    cs = _make_call_session(deal.id, sh.id)
    extraction = _make_extraction(cs.id)

    db = RiskSession(
        call_session=cs,
        deal=deal,
        extraction=extraction,
        stakeholders=[sh],
        prev_risk=None,
    )

    result = await run_risk_update(
        db, cs.id,  # type: ignore[arg-type]
    )

    assert result is not None
    assert isinstance(result, RiskSnapshot)
    assert result.score >= 0
    assert result.level in ("low", "medium", "high", "critical")
    assert db.committed >= 2

    sh_snaps = [
        a
        for a in db.added
        if isinstance(a, StakeholderSnapshot)
    ]
    deal_snaps = [
        a
        for a in db.added
        if isinstance(a, DealSnapshot)
    ]
    risk_snaps = [
        a
        for a in db.added
        if isinstance(a, RiskSnapshot)
    ]
    assert len(sh_snaps) == 1
    assert len(deal_snaps) == 1
    assert len(risk_snaps) == 1
    assert deal_snaps[0].coverage_status == "full"


@pytest.mark.asyncio
async def test_run_risk_update_skips_wrong_status() -> None:
    cs = CallSession(
        id=uuid.uuid4(),
        deal_id=uuid.uuid4(),
        stakeholder_id=uuid.uuid4(),
        provider_name="bolna",
        status="completed",
        processing_status="transcript_finalized",
    )
    cs.created_at = datetime.now(timezone.utc)
    cs.updated_at = datetime.now(timezone.utc)

    db = RiskSession(call_session=cs)

    result = await run_risk_update(
        db, cs.id,  # type: ignore[arg-type]
    )

    assert result is None


@pytest.mark.asyncio
async def test_run_risk_update_skips_fresh_snapshots_updating() -> None:
    cs = CallSession(
        id=uuid.uuid4(),
        deal_id=uuid.uuid4(),
        stakeholder_id=uuid.uuid4(),
        provider_name="bolna",
        status="completed",
        processing_status="snapshots_updating",
    )
    cs.created_at = datetime.now(timezone.utc)
    cs.updated_at = datetime.now(timezone.utc)

    db = RiskSession(call_session=cs)

    result = await run_risk_update(
        db, cs.id,  # type: ignore[arg-type]
    )

    assert result is None


@pytest.mark.asyncio
async def test_run_risk_update_retries_stale_snapshots_updating() -> None:
    org_id = uuid.uuid4()
    deal = _make_deal(org_id)
    sh = _make_stakeholder(deal.id)
    cs = _make_call_session(deal.id, sh.id)
    cs.processing_status = "snapshots_updating"
    cs.updated_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    extraction = _make_extraction(cs.id)

    db = RiskSession(
        call_session=cs,
        deal=deal,
        extraction=extraction,
        stakeholders=[sh],
        prev_risk=None,
    )

    result = await run_risk_update(
        db, cs.id,  # type: ignore[arg-type]
    )

    assert result is not None


@pytest.mark.asyncio
async def test_run_risk_update_with_previous_snapshot() -> None:
    org_id = uuid.uuid4()
    deal = _make_deal(org_id)
    sh = _make_stakeholder(deal.id)
    cs = _make_call_session(deal.id, sh.id)
    extraction = _make_extraction(cs.id)

    prev = RiskSnapshot(
        id=uuid.uuid4(),
        deal_id=deal.id,
        score=20,
        level="low",
        factors_json={"factors": ["Old factor"]},
    )
    prev.created_at = datetime.now(timezone.utc)

    db = RiskSession(
        call_session=cs,
        deal=deal,
        extraction=extraction,
        stakeholders=[sh],
        prev_risk=prev,
    )

    result = await run_risk_update(
        db, cs.id,  # type: ignore[arg-type]
    )

    assert result is not None
    changes = result.change_summary_json or {}
    assert "changes" in changes
    assert len(changes["changes"]) > 0


@pytest.mark.asyncio
async def test_run_risk_update_missing_extraction_is_retryable() -> None:
    org_id = uuid.uuid4()
    deal = _make_deal(org_id)
    sh = _make_stakeholder(deal.id)
    cs = _make_call_session(deal.id, sh.id)

    db = RiskSession(
        call_session=cs,
        deal=deal,
        extraction=None,
        stakeholders=[sh],
        prev_risk=None,
    )

    with pytest.raises(RetryableRiskError):
        await run_risk_update(
            db, cs.id,  # type: ignore[arg-type]
        )

    assert db.committed >= 2
