"""Tests for recommendation pipeline."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest
from conftest import FakeScalarsResult

from app.models.action_recommendation import ActionRecommendation
from app.models.call_session import CallSession
from app.models.deal import Deal
from app.models.extraction_snapshot import ExtractionSnapshot
from app.models.followup_draft import FollowupDraft
from app.models.risk_snapshot import RiskSnapshot
from app.models.stakeholder import Stakeholder
from app.services.recommendation.schema import (
    FollowupDraftItem,
    RecommendationItem,
    RecommendationOutput,
)
from app.services.recommendation.service import (
    RetryableRecommendationError,
    _fallback_recommendation,
    run_recommendation,
)


class _FakeUpdateResult:
    pass


class RecSession:
    """Fake DB session for recommendation tests."""

    def __init__(
        self,
        call_session: CallSession | None = None,
        deal: Deal | None = None,
        extraction: ExtractionSnapshot | None = None,
        risk: RiskSnapshot | None = None,
        stakeholders: list[Stakeholder] | None = None,
    ) -> None:
        self._select_responses: list[Any] = [
            call_session,
            deal,
            extraction,
            risk,
            stakeholders or [],
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

    async def refresh(self, _instance: Any) -> None:
        pass


def _make_call_session(
    deal_id: uuid.UUID,
    stakeholder_id: uuid.UUID,
    *,
    processing_status: str = "risk_running",
) -> CallSession:
    cs = CallSession(
        id=uuid.uuid4(),
        deal_id=deal_id,
        stakeholder_id=stakeholder_id,
        provider_name="bolna",
        status="completed",
        processing_status=processing_status,
        objective="discovery_qualification",
    )
    cs.created_at = datetime.now(timezone.utc)
    cs.updated_at = datetime.now(timezone.utc)
    return cs


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
    ext = ExtractionSnapshot(
        id=uuid.uuid4(),
        call_session_id=call_session_id,
        schema_version="1.0",
        prompt_version="1.0",
        model_name="gemini-2.5-flash",
        extracted_json={
            "stakeholder": {
                "name": "Jane",
                "role_label": "champion",
            },
            "deal_signals": {
                "next_step": "",
                "objections": ["pricing"],
            },
            "interaction": {"sentiment": "positive"},
        },
        summary="Good discovery call.",
        confidence=0.85,
    )
    ext.created_at = datetime.now(timezone.utc)
    return ext


def _make_risk(deal_id: uuid.UUID) -> RiskSnapshot:
    r = RiskSnapshot(
        id=uuid.uuid4(),
        deal_id=deal_id,
        score=45,
        level="medium",
        factors_json={
            "factors": [
                "No committed next step",
                "No economic buyer identified",
            ],
        },
    )
    r.created_at = datetime.now(timezone.utc)
    return r


# --- Fallback tests ---


def test_fallback_no_next_step() -> None:
    ext = MagicMock()
    ext.summary = "Summary."
    risk = MagicMock()
    risk.factors_json = {
        "factors": ["No committed next step"],
    }

    output = _fallback_recommendation(ext, risk)

    assert len(output.recommendations) == 1
    assert output.recommendations[0].action_type == (
        "send_followup"
    )
    assert len(output.drafts) == 1
    assert output.drafts[0].draft_type == "crm_note"


def test_fallback_no_economic_buyer() -> None:
    ext = MagicMock()
    ext.summary = "Summary."
    risk = MagicMock()
    risk.factors_json = {
        "factors": ["No economic buyer identified"],
    }

    output = _fallback_recommendation(ext, risk)

    assert output.recommendations[0].action_type == (
        "request_intro"
    )


def test_fallback_generic() -> None:
    ext = MagicMock()
    ext.summary = "Summary."
    risk = MagicMock()
    risk.factors_json = {"factors": ["Some other factor"]}

    output = _fallback_recommendation(ext, risk)

    assert output.recommendations[0].action_type == (
        "send_followup"
    )
    assert output.drafts[0].draft_type == "crm_note"


# --- Schema tests ---


def test_recommendation_output_schema() -> None:
    output = RecommendationOutput(
        recommendations=[
            RecommendationItem(
                action_type="call_stakeholder",
                reason="Follow up on the deal.",
                confidence=0.8,
            ),
        ],
        drafts=[
            FollowupDraftItem(
                draft_type="crm_note",
                body_text="Call completed.",
            ),
        ],
    )
    assert len(output.recommendations) == 1
    assert len(output.drafts) == 1


# --- Service integration tests ---


@pytest.mark.asyncio
async def test_run_recommendation_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deal = _make_deal()
    sh = Stakeholder(
        id=uuid.uuid4(),
        deal_id=deal.id,
        name="Jane",
        source_type="manual",
    )
    sh.created_at = datetime.now(timezone.utc)
    sh.updated_at = datetime.now(timezone.utc)
    cs = _make_call_session(deal.id, sh.id)
    ext = _make_extraction(cs.id)
    risk = _make_risk(deal.id)

    db = RecSession(
        call_session=cs,
        deal=deal,
        extraction=ext,
        risk=risk,
        stakeholders=[sh],
    )

    output = RecommendationOutput(
        recommendations=[
            RecommendationItem(
                action_type="send_followup",
                reason="Re-establish momentum.",
                confidence=0.75,
                talk_track="Reference the pricing concern.",
            ),
        ],
        drafts=[
            FollowupDraftItem(
                draft_type="crm_note",
                body_text="Good discovery call.",
            ),
            FollowupDraftItem(
                draft_type="email",
                subject="Follow up on our call",
                body_text="Hi Jane...",
                tone="professional",
            ),
        ],
    )

    fake_settings = MagicMock()
    fake_settings.GEMINI_API_KEY = "test-key"
    fake_settings.GEMINI_MODEL_RECOMMENDATION = "gemini-pro"
    monkeypatch.setattr(
        "app.services.recommendation.service.get_settings",
        lambda: fake_settings,
    )

    fake_response = MagicMock()
    fake_response.text = output.model_dump_json()
    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = (
        fake_response
    )
    monkeypatch.setattr(
        "app.services.recommendation.service.genai.Client",
        lambda api_key: fake_client,
    )

    recs = await run_recommendation(
        db, cs.id,  # type: ignore[arg-type]
    )

    assert len(recs) == 1
    assert recs[0].action_type == "send_followup"
    assert db.committed >= 1

    rec_models = [
        a for a in db.added
        if isinstance(a, ActionRecommendation)
    ]
    draft_models = [
        a for a in db.added
        if isinstance(a, FollowupDraft)
    ]
    assert len(rec_models) == 1
    assert len(draft_models) == 2
    assert any(
        d.draft_type == "crm_note" for d in draft_models
    )


@pytest.mark.asyncio
async def test_run_recommendation_gemini_failure_uses_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When Gemini fails, fallback generates a rec + CRM note."""
    deal = _make_deal()
    sh = Stakeholder(
        id=uuid.uuid4(),
        deal_id=deal.id,
        name="Jane",
        source_type="manual",
    )
    sh.created_at = datetime.now(timezone.utc)
    sh.updated_at = datetime.now(timezone.utc)
    cs = _make_call_session(deal.id, sh.id)
    ext = _make_extraction(cs.id)
    risk = _make_risk(deal.id)

    db = RecSession(
        call_session=cs,
        deal=deal,
        extraction=ext,
        risk=risk,
        stakeholders=[sh],
    )

    fake_settings = MagicMock()
    fake_settings.GEMINI_API_KEY = "test-key"
    fake_settings.GEMINI_MODEL_RECOMMENDATION = "gemini-pro"
    monkeypatch.setattr(
        "app.services.recommendation.service.get_settings",
        lambda: fake_settings,
    )

    fake_client = MagicMock()
    fake_client.models.generate_content.side_effect = (
        RuntimeError("API down")
    )
    monkeypatch.setattr(
        "app.services.recommendation.service.genai.Client",
        lambda api_key: fake_client,
    )

    recs = await run_recommendation(
        db, cs.id,  # type: ignore[arg-type]
    )

    assert len(recs) >= 1
    assert db.committed >= 1

    drafts = [
        a for a in db.added
        if isinstance(a, FollowupDraft)
    ]
    assert any(d.draft_type == "crm_note" for d in drafts)


@pytest.mark.asyncio
async def test_run_recommendation_skips_wrong_status() -> None:
    cs = _make_call_session(
        uuid.uuid4(),
        uuid.uuid4(),
        processing_status="extraction_completed",
    )

    db = RecSession(call_session=cs)

    recs = await run_recommendation(
        db, cs.id,  # type: ignore[arg-type]
    )

    assert recs == []


@pytest.mark.asyncio
async def test_run_recommendation_missing_context_is_retryable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deal = _make_deal()
    sh = Stakeholder(
        id=uuid.uuid4(),
        deal_id=deal.id,
        name="Jane",
        source_type="manual",
    )
    sh.created_at = datetime.now(timezone.utc)
    sh.updated_at = datetime.now(timezone.utc)
    cs = _make_call_session(deal.id, sh.id)

    db = RecSession(
        call_session=cs,
        deal=deal,
        extraction=None,
        risk=None,
        stakeholders=[sh],
    )

    fake_settings = MagicMock()
    fake_settings.GEMINI_API_KEY = "test-key"
    fake_settings.GEMINI_MODEL_RECOMMENDATION = "gemini-pro"
    monkeypatch.setattr(
        "app.services.recommendation.service.get_settings",
        lambda: fake_settings,
    )

    with pytest.raises(RetryableRecommendationError):
        await run_recommendation(
            db, cs.id,  # type: ignore[arg-type]
        )


@pytest.mark.asyncio
async def test_run_recommendation_skips_fresh_running_claim(
) -> None:
    cs = _make_call_session(
        uuid.uuid4(),
        uuid.uuid4(),
        processing_status="recommendation_running",
    )
    cs.updated_at = datetime.now(timezone.utc)
    db = RecSession(call_session=cs)

    recs = await run_recommendation(
        db, cs.id,  # type: ignore[arg-type]
    )

    assert recs == []


@pytest.mark.asyncio
async def test_run_recommendation_recovers_stale_running_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deal = _make_deal()
    sh = Stakeholder(
        id=uuid.uuid4(),
        deal_id=deal.id,
        name="Jane",
        source_type="manual",
    )
    sh.created_at = datetime.now(timezone.utc)
    sh.updated_at = datetime.now(timezone.utc)
    cs = _make_call_session(
        deal.id,
        sh.id,
        processing_status="recommendation_running",
    )
    cs.updated_at = datetime.now(timezone.utc) - timedelta(
        minutes=2,
    )
    ext = _make_extraction(cs.id)
    risk = _make_risk(deal.id)

    db = RecSession(
        call_session=cs,
        deal=deal,
        extraction=ext,
        risk=risk,
        stakeholders=[sh],
    )

    output = RecommendationOutput(
        recommendations=[
            RecommendationItem(
                action_type="send_followup",
                reason="Re-establish momentum.",
                confidence=0.75,
            ),
        ],
        drafts=[
            FollowupDraftItem(
                draft_type="crm_note",
                body_text="Good discovery call.",
            ),
        ],
    )

    fake_settings = MagicMock()
    fake_settings.GEMINI_API_KEY = "test-key"
    fake_settings.GEMINI_MODEL_RECOMMENDATION = "gemini-pro"
    monkeypatch.setattr(
        "app.services.recommendation.service.get_settings",
        lambda: fake_settings,
    )

    fake_response = MagicMock()
    fake_response.text = output.model_dump_json()
    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = (
        fake_response
    )
    monkeypatch.setattr(
        "app.services.recommendation.service.genai.Client",
        lambda api_key: fake_client,
    )

    recs = await run_recommendation(
        db, cs.id,  # type: ignore[arg-type]
    )

    assert len(recs) == 1
