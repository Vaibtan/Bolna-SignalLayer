"""Unit tests for the deal service layer."""

import uuid
from typing import Any

import pytest
from conftest import FakeResult, FakeScalarsResult, FakeSession

from app.core.exceptions import NotFoundError
from app.models.deal import Deal
from app.schemas.deal import DealCreate, DealUpdate
from app.services.deal import service as deal_svc


class DealSession(FakeSession):
    """Session stub that supports CRUD-style queries for deals."""

    def __init__(
        self,
        deals: list[Deal] | None = None,
        execute_results: list[object] | None = None,
    ) -> None:
        super().__init__()
        self._deals = deals or []
        self._execute_results = iter(execute_results or [])

    async def execute(self, stmt: object) -> Any:
        next_result = next(self._execute_results, None)
        if next_result is not None:
            if isinstance(next_result, list):
                return FakeScalarsResult(next_result)
            return FakeResult(next_result)

        return FakeScalarsResult(self._deals)


@pytest.mark.asyncio
async def test_create_deal_adds_to_session() -> None:
    owner_id = uuid.uuid4()
    session = DealSession(execute_results=[owner_id])
    payload = DealCreate(
        name='Test Deal',
        account_name='Test Account',
        stage='discovery',
        owner_user_id=owner_id,
    )
    org_id = uuid.uuid4()

    deal = await deal_svc.create_deal(session, org_id, payload)  # type: ignore[arg-type]

    assert deal.name == "Test Deal"
    assert deal.account_name == "Test Account"
    assert deal.org_id == org_id
    assert len(session.added) == 1


@pytest.mark.asyncio
async def test_create_deal_rejects_owner_from_other_org() -> None:
    session = DealSession(execute_results=[None])
    payload = DealCreate(
        name='Test Deal',
        account_name='Test Account',
        stage='discovery',
        owner_user_id=uuid.uuid4(),
    )

    with pytest.raises(NotFoundError):
        await deal_svc.create_deal(
            session,  # type: ignore[arg-type]
            uuid.uuid4(),
            payload,
        )


@pytest.mark.asyncio
async def test_get_deal_raises_not_found_when_missing() -> None:
    session = DealSession(deals=[])

    with pytest.raises(NotFoundError):
        await deal_svc.get_deal(session, uuid.uuid4(), uuid.uuid4())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_list_deals_returns_org_deals() -> None:
    deal = Deal(
        id=uuid.uuid4(),
        org_id=uuid.uuid4(),
        name="D1",
        account_name="A1",
        stage="discovery",
    )
    session = DealSession(deals=[deal])

    result = await deal_svc.list_deals(session, deal.org_id)  # type: ignore[arg-type]

    assert len(result) == 1
    assert result[0].name == "D1"


@pytest.mark.asyncio
async def test_update_deal_raises_not_found() -> None:
    session = DealSession(execute_results=[None])
    payload = DealUpdate(name="Updated")

    with pytest.raises(NotFoundError):
        await deal_svc.update_deal(session, uuid.uuid4(), uuid.uuid4(), payload)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_update_deal_rejects_owner_from_other_org() -> None:
    session = DealSession(execute_results=[None])
    payload = DealUpdate(owner_user_id=uuid.uuid4())

    with pytest.raises(NotFoundError):
        await deal_svc.update_deal(
            session,  # type: ignore[arg-type]
            uuid.uuid4(),
            uuid.uuid4(),
            payload,
        )
