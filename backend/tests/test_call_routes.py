"""Route tests for call endpoints."""

import uuid
from datetime import datetime, timezone

import pytest
from conftest import build_user, override_db
from httpx import AsyncClient

from app.api.deps import get_current_user
from app.db.session import get_db_session
from app.main import app
from app.models.call_session import CallSession
from app.models.user import User
from app.services.call import service as call_svc


def _make_call_session(
    deal_id: uuid.UUID,
    status: str = "queued",
) -> CallSession:
    now = datetime.now(timezone.utc)
    cs = CallSession(
        id=uuid.uuid4(),
        deal_id=deal_id,
        stakeholder_id=uuid.uuid4(),
        provider_name="bolna",
        provider_call_id="mock-abc",
        status=status,
        processing_status="pending",
        objective="discovery_qualification",
    )
    cs.created_at = now
    cs.updated_at = now
    return cs


@pytest.mark.asyncio
async def test_initiate_call_returns_201(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
) -> None:
    user = build_user()
    deal_id = uuid.uuid4()
    cs = _make_call_session(deal_id)
    cs.initiated_by_user_id = user.id

    async def fake_initiate(
        *_a: object, **_kw: object,
    ) -> CallSession:
        return cs

    monkeypatch.setattr(
        call_svc, 'initiate_call', fake_initiate,
    )
    enqueued: list[str] = []
    monkeypatch.setattr(
        call_svc, 'enqueue_poll', enqueued.append,
    )

    async def _user() -> User:
        return user

    app.dependency_overrides[get_current_user] = _user
    app.dependency_overrides[get_db_session] = override_db

    response = await client.post(
        f'/api/deals/{deal_id}/calls',
        json={
            'stakeholder_id': str(uuid.uuid4()),
            'objective': 'discovery_qualification',
        },
    )

    assert response.status_code == 201
    assert response.json()['status'] == 'queued'
    assert response.json()['provider_name'] == 'bolna'
    assert enqueued == [str(cs.id)]


@pytest.mark.asyncio
async def test_initiate_call_returns_502_on_provider_failure(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
) -> None:
    user = build_user()
    deal_id = uuid.uuid4()
    cs = _make_call_session(deal_id, status="failed")
    cs.initiated_by_user_id = user.id

    async def fake_initiate(
        *_a: object, **_kw: object,
    ) -> CallSession:
        return cs

    monkeypatch.setattr(
        call_svc, 'initiate_call', fake_initiate,
    )
    enqueued: list[str] = []
    monkeypatch.setattr(
        call_svc, 'enqueue_poll', enqueued.append,
    )

    async def _user() -> User:
        return user

    app.dependency_overrides[get_current_user] = _user
    app.dependency_overrides[get_db_session] = override_db

    response = await client.post(
        f'/api/deals/{deal_id}/calls',
        json={
            'stakeholder_id': str(uuid.uuid4()),
            'objective': 'discovery_qualification',
        },
    )

    assert response.status_code == 502
    assert 'provider could not' in response.json()['detail']
    assert enqueued == []


@pytest.mark.asyncio
async def test_get_call_returns_session(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
) -> None:
    user = build_user()
    deal_id = uuid.uuid4()
    cs = _make_call_session(deal_id)

    async def fake_get(
        *_a: object, **_kw: object,
    ) -> CallSession:
        return cs

    monkeypatch.setattr(
        call_svc, 'get_call_session', fake_get,
    )

    async def _user() -> User:
        return user

    app.dependency_overrides[get_current_user] = _user
    app.dependency_overrides[get_db_session] = override_db

    response = await client.get(f'/api/calls/{cs.id}')

    assert response.status_code == 200
    assert response.json()['id'] == str(cs.id)


@pytest.mark.asyncio
async def test_call_routes_require_auth(
    client: AsyncClient,
) -> None:
    app.dependency_overrides[get_db_session] = override_db
    deal_id = str(uuid.uuid4())

    response = await client.post(
        f'/api/deals/{deal_id}/calls',
        json={
            'stakeholder_id': str(uuid.uuid4()),
            'objective': 'discovery_qualification',
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_initiate_call_rejects_invalid_objective(
    client: AsyncClient,
) -> None:
    user = build_user()

    async def _user() -> User:
        return user

    app.dependency_overrides[get_current_user] = _user
    app.dependency_overrides[get_db_session] = override_db

    response = await client.post(
        f'/api/deals/{uuid.uuid4()}/calls',
        json={
            'stakeholder_id': str(uuid.uuid4()),
            'objective': 'invalid_objective',
        },
    )

    assert response.status_code == 422
