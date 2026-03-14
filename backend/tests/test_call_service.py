"""Unit tests for the call initiation service."""

import uuid
from typing import Any

import pytest
from conftest import FakeRedis, FakeResult, FakeScalarsResult, FakeSession

from app.core.exceptions import NotFoundError, RateLimitError
from app.models.call_session import CallSession
from app.models.deal import Deal
from app.models.extraction_snapshot import ExtractionSnapshot
from app.models.stakeholder import Stakeholder
from app.services.bolna.adapter import (
    BolnaAdapter,
    CallRequest,
    CallResponse,
)
from app.services.call import service as call_svc


def _make_deal(
    org_id: uuid.UUID | None = None,
) -> Deal:
    return Deal(
        id=uuid.uuid4(),
        org_id=org_id or uuid.uuid4(),
        name="Test Deal",
        account_name="Test Corp",
        stage="discovery",
    )


def _make_stakeholder(deal_id: uuid.UUID) -> Stakeholder:
    return Stakeholder(
        id=uuid.uuid4(),
        deal_id=deal_id,
        name="Jane",
        phone="+15551234567",
    )


class FakeAdapter(BolnaAdapter):
    """Adapter stub returning configurable responses."""

    def __init__(
        self, response: CallResponse | None = None,
    ) -> None:
        self._response = response or CallResponse(
            provider_call_id="mock-abc123",
            raw_response={
                "execution_id": "mock-abc123",
                "status": "queued",
            },
        )

    async def initiate_call(
        self, request: CallRequest,
    ) -> CallResponse:
        self.last_request = request
        return self._response

    async def get_execution(
        self, execution_id: str,
    ) -> dict[str, Any]:
        return {"execution_id": execution_id}


class CallSession_(FakeSession):
    """Session stub with ordered execute results."""

    def __init__(self, results: list[object]) -> None:
        super().__init__()
        self._results = iter(results)

    async def execute(self, stmt: object) -> FakeResult:
        return FakeResult(next(self._results, None))


class RedactionSession(FakeSession):
    """Session stub for transcript redaction and retention tests."""

    def __init__(self, results: list[object]) -> None:
        super().__init__()
        self._results = iter(results)
        self.executed: list[object] = []
        self.commit_count = 0

    async def execute(self, stmt: object) -> object:
        self.executed.append(stmt)
        value = next(self._results, None)
        if isinstance(value, list):
            return FakeScalarsResult(value)
        return FakeResult(value)

    async def commit(self) -> None:
        self.commit_count += 1


@pytest.mark.asyncio
async def test_initiate_call_success() -> None:
    deal = _make_deal()
    stakeholder = _make_stakeholder(deal.id)
    adapter = FakeAdapter()
    redis = FakeRedis()

    session = CallSession_(results=[deal, stakeholder, None])

    call = await call_svc.initiate_call(
        db=session,  # type: ignore[arg-type]
        redis=redis,  # type: ignore[arg-type]
        adapter=adapter,
        org_id=deal.org_id,
        deal_id=deal.id,
        user_id=uuid.uuid4(),
        stakeholder_id=stakeholder.id,
        objective="discovery_qualification",
    )

    assert isinstance(call, CallSession)
    assert call.status == "queued"
    assert call.provider_call_id == "mock-abc123"
    assert len(session.added) == 1
    # Session committed before provider call
    assert session.committed is True
    assert call.provider_metadata_json == {
        'request': {
            'agent_id': '',
            'recipient_phone_number': stakeholder.phone,
            'user_data': {
                'stakeholder_name': stakeholder.name,
                'stakeholder_title': '',
                'company_name': deal.account_name,
                'deal_context': 'Test Deal. discovery stage engagement.',
                'call_objective': 'discovery_qualification',
            },
        },
        'response': {
            'execution_id': 'mock-abc123',
            'status': 'queued',
        },
    }


@pytest.mark.asyncio
async def test_initiate_call_deal_not_found() -> None:
    adapter = FakeAdapter()
    redis = FakeRedis()
    session = CallSession_(results=[None])

    with pytest.raises(NotFoundError, match="Deal not found"):
        await call_svc.initiate_call(
            db=session,  # type: ignore[arg-type]
            redis=redis,  # type: ignore[arg-type]
            adapter=adapter,
            org_id=uuid.uuid4(),
            deal_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            stakeholder_id=uuid.uuid4(),
            objective="discovery_qualification",
        )


@pytest.mark.asyncio
async def test_initiate_call_stakeholder_not_found() -> None:
    deal = _make_deal()
    adapter = FakeAdapter()
    redis = FakeRedis()
    session = CallSession_(results=[deal, None])

    with pytest.raises(
        NotFoundError, match="Stakeholder not found",
    ):
        await call_svc.initiate_call(
            db=session,  # type: ignore[arg-type]
            redis=redis,  # type: ignore[arg-type]
            adapter=adapter,
            org_id=deal.org_id,
            deal_id=deal.id,
            user_id=uuid.uuid4(),
            stakeholder_id=uuid.uuid4(),
            objective="discovery_qualification",
        )


@pytest.mark.asyncio
async def test_initiate_call_no_phone() -> None:
    deal = _make_deal()
    stakeholder = Stakeholder(
        id=uuid.uuid4(),
        deal_id=deal.id,
        name="No Phone",
        phone=None,
    )
    adapter = FakeAdapter()
    redis = FakeRedis()
    session = CallSession_(results=[deal, stakeholder, None])

    with pytest.raises(NotFoundError, match="no phone number"):
        await call_svc.initiate_call(
            db=session,  # type: ignore[arg-type]
            redis=redis,  # type: ignore[arg-type]
            adapter=adapter,
            org_id=deal.org_id,
            deal_id=deal.id,
            user_id=uuid.uuid4(),
            stakeholder_id=stakeholder.id,
            objective="discovery_qualification",
        )


@pytest.mark.asyncio
async def test_user_rate_limited_via_atomic_incr() -> None:
    """INCR is atomic — pre-filled counter at limit triggers 429."""
    deal = _make_deal()
    stakeholder = _make_stakeholder(deal.id)
    adapter = FakeAdapter()
    redis = FakeRedis()

    user_id = uuid.uuid4()
    # Pre-fill at the limit; INCR will push it to 4 > 3.
    key = f"dealgraph:ratelimit:call_init:user:{user_id}"
    redis.store[key] = "3"
    redis.ttls[key] = 120

    session = CallSession_(results=[deal, stakeholder, None])

    with pytest.raises(RateLimitError):
        await call_svc.initiate_call(
            db=session,  # type: ignore[arg-type]
            redis=redis,  # type: ignore[arg-type]
            adapter=adapter,
            org_id=deal.org_id,
            deal_id=deal.id,
            user_id=user_id,
            stakeholder_id=stakeholder.id,
            objective="discovery_qualification",
        )


@pytest.mark.asyncio
async def test_stakeholder_cooldown_via_setnx() -> None:
    """SET NX is atomic — existing key blocks the second call."""
    deal = _make_deal()
    stakeholder = _make_stakeholder(deal.id)
    adapter = FakeAdapter()
    redis = FakeRedis()

    # Pre-fill the stakeholder cooldown key.
    key = (
        f"dealgraph:ratelimit"
        f":call_init:stakeholder:{stakeholder.id}"
    )
    redis.store[key] = "1"
    redis.ttls[key] = 200

    session = CallSession_(results=[deal, stakeholder, None])

    with pytest.raises(RateLimitError):
        await call_svc.initiate_call(
            db=session,  # type: ignore[arg-type]
            redis=redis,  # type: ignore[arg-type]
            adapter=adapter,
            org_id=deal.org_id,
            deal_id=deal.id,
            user_id=uuid.uuid4(),
            stakeholder_id=stakeholder.id,
            objective="discovery_qualification",
        )


@pytest.mark.asyncio
async def test_provider_failure_persists_failed_session(
) -> None:
    """Provider failure still persists the session and consumes
    the failed session without leaking reserved slots."""
    deal = _make_deal()
    stakeholder = _make_stakeholder(deal.id)
    failed_response = CallResponse(
        provider_call_id="",
        raw_response={"error": "timeout"},
        success=False,
        error_message="Bolna connection error",
    )
    adapter = FakeAdapter(response=failed_response)
    redis = FakeRedis()

    session = CallSession_(results=[deal, stakeholder, None])

    call = await call_svc.initiate_call(
        db=session,  # type: ignore[arg-type]
        redis=redis,  # type: ignore[arg-type]
        adapter=adapter,
        org_id=deal.org_id,
        deal_id=deal.id,
        user_id=uuid.uuid4(),
        stakeholder_id=stakeholder.id,
        objective="blocker_clarification",
    )

    assert call.status == "failed"
    assert len(session.added) == 1
    assert redis.store == {}
    assert redis.ttls == {}
    assert call.provider_metadata_json == {
        'request': {
            'agent_id': '',
            'recipient_phone_number': stakeholder.phone,
            'user_data': {
                'stakeholder_name': stakeholder.name,
                'stakeholder_title': '',
                'company_name': deal.account_name,
                'deal_context': 'Test Deal. discovery stage engagement.',
                'call_objective': 'blocker_clarification',
            },
        },
        'response': {'error': 'timeout'},
        'error': 'Bolna connection error',
    }


@pytest.mark.asyncio
async def test_success_records_rate_limit_slots() -> None:
    """Successful call consumes both user and stakeholder slots."""
    deal = _make_deal()
    stakeholder = _make_stakeholder(deal.id)
    adapter = FakeAdapter()
    redis = FakeRedis()
    user_id = uuid.uuid4()

    session = CallSession_(results=[deal, stakeholder, None])

    await call_svc.initiate_call(
        db=session,  # type: ignore[arg-type]
        redis=redis,  # type: ignore[arg-type]
        adapter=adapter,
        org_id=deal.org_id,
        deal_id=deal.id,
        user_id=user_id,
        stakeholder_id=stakeholder.id,
        objective="discovery_qualification",
    )

    user_key = (
        f"dealgraph:ratelimit:call_init:user:{user_id}"
    )
    sh_key = (
        f"dealgraph:ratelimit"
        f":call_init:stakeholder:{stakeholder.id}"
    )
    assert user_key in redis.store
    assert sh_key in redis.store


@pytest.mark.asyncio
async def test_stakeholder_rate_limit_releases_user_slot() -> None:
    """A stakeholder cooldown failure must not consume user quota."""
    deal = _make_deal()
    stakeholder = _make_stakeholder(deal.id)
    adapter = FakeAdapter()
    redis = FakeRedis()
    user_id = uuid.uuid4()

    sh_key = (
        f"dealgraph:ratelimit"
        f":call_init:stakeholder:{stakeholder.id}"
    )
    redis.store[sh_key] = "1"
    redis.ttls[sh_key] = 200

    session = CallSession_(results=[deal, stakeholder, None])

    with pytest.raises(RateLimitError):
        await call_svc.initiate_call(
            db=session,  # type: ignore[arg-type]
            redis=redis,  # type: ignore[arg-type]
            adapter=adapter,
            org_id=deal.org_id,
            deal_id=deal.id,
            user_id=user_id,
            stakeholder_id=stakeholder.id,
            objective="discovery_qualification",
        )

    user_key = (
        f"dealgraph:ratelimit:call_init:user:{user_id}"
    )
    assert user_key not in redis.store


@pytest.mark.asyncio
async def test_context_caps_and_known_context_from_extraction() -> None:
    deal = _make_deal()
    deal.summary_current = (
        "Sentence one. Sentence two. Sentence three. Sentence four."
    )
    stakeholder = _make_stakeholder(deal.id)
    stakeholder.title = "VP Procurement"
    stakeholder.stance_current = "skeptical"
    adapter = FakeAdapter()
    redis = FakeRedis()
    extraction = ExtractionSnapshot(
        id=uuid.uuid4(),
        call_session_id=uuid.uuid4(),
        schema_version='v1',
        prompt_version='p1',
        model_name='gemini-2.5-flash',
        extracted_json={'summary': 'unused'},
        summary=(
            "Latest summary one. Latest summary two. "
            "Latest summary three."
        ),
        confidence=0.9,
    )
    session = CallSession_(results=[deal, stakeholder, extraction.summary])

    await call_svc.initiate_call(
        db=session,  # type: ignore[arg-type]
        redis=redis,  # type: ignore[arg-type]
        adapter=adapter,
        org_id=deal.org_id,
        deal_id=deal.id,
        user_id=uuid.uuid4(),
        stakeholder_id=stakeholder.id,
        objective='discovery_qualification',
        topics='Question one?\nQuestion two?\nQuestion three?',
    )

    user_data = adapter.last_request.user_data
    assert user_data['deal_context'] == (
        'Sentence one. Sentence two. Sentence three.'
    )
    assert user_data['open_questions'] == [
        'Question one?',
        'Question two?',
    ]
    assert user_data['known_context'] == (
        'Latest summary one. Latest summary two.'
    )


@pytest.mark.asyncio
async def test_redact_call_artifacts_commits() -> None:
    call_id = uuid.uuid4()
    session = RedactionSession(results=[None] * 7)

    await call_svc.redact_call_artifacts(
        session,  # type: ignore[arg-type]
        call_id,
    )

    assert session.commit_count == 1
    assert len(session.executed) == 7


@pytest.mark.asyncio
async def test_apply_transcript_retention_redacts_expired_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expired_call_id = uuid.uuid4()
    session = RedactionSession(
        results=[[expired_call_id], None, None, None, None, None, None, None],
    )

    class _Settings:
        TRANSCRIPT_RETENTION_DAYS = 30

    monkeypatch.setattr(
        call_svc, 'get_settings', lambda: _Settings(),
    )

    count = await call_svc.apply_transcript_retention(
        session,  # type: ignore[arg-type]
    )

    assert count == 1
    assert session.commit_count == 1
    assert len(session.executed) == 8
