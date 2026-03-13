"""Route tests for deal and stakeholder endpoints."""

import uuid
from datetime import datetime, timezone

import pytest
from conftest import build_user, override_db
from httpx import AsyncClient

from app.api.deps import get_current_user
from app.db.session import get_db_session
from app.main import app
from app.models.deal import Deal
from app.models.user import User
from app.services.deal import service as deal_svc


def _make_deal(org_id: uuid.UUID) -> Deal:
    now = datetime.now(timezone.utc)
    d = Deal(
        id=uuid.uuid4(),
        org_id=org_id,
        name="Test Deal",
        account_name="Test Corp",
        stage="discovery",
    )
    d.created_at = now
    d.updated_at = now
    return d


@pytest.mark.asyncio
async def test_create_deal_returns_201(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
) -> None:
    user = build_user()
    deal = _make_deal(user.org_id)

    async def fake_create(*_a: object, **_kw: object) -> Deal:
        return deal

    monkeypatch.setattr(deal_svc, 'create_deal', fake_create)

    async def _user() -> User:
        return user

    app.dependency_overrides[get_current_user] = _user
    app.dependency_overrides[get_db_session] = override_db

    response = await client.post(
        '/api/deals',
        json={
            'name': 'Test Deal',
            'account_name': 'Test Corp',
            'stage': 'discovery',
        },
    )

    assert response.status_code == 201
    assert response.json()['name'] == 'Test Deal'



@pytest.mark.asyncio
async def test_list_deals_returns_org_deals(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
) -> None:
    user = build_user()
    deal = _make_deal(user.org_id)

    async def fake_list(*_a: object, **_kw: object) -> list[Deal]:
        return [deal]

    monkeypatch.setattr(deal_svc, 'list_deals', fake_list)

    async def _user() -> User:
        return user

    app.dependency_overrides[get_current_user] = _user
    app.dependency_overrides[get_db_session] = override_db

    response = await client.get('/api/deals')

    assert response.status_code == 200
    assert len(response.json()) == 1



@pytest.mark.asyncio
async def test_list_deals_requires_auth(client: AsyncClient) -> None:
    app.dependency_overrides[get_db_session] = override_db

    response = await client.get('/api/deals')

    assert response.status_code == 401



@pytest.mark.asyncio
async def test_stakeholder_routes_require_auth(client: AsyncClient) -> None:
    app.dependency_overrides[get_db_session] = override_db
    deal_id = str(uuid.uuid4())

    response = await client.get(f'/api/deals/{deal_id}/stakeholders')

    assert response.status_code == 401

