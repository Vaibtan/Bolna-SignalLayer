"""Unit tests for the stakeholder service layer."""

import uuid
from typing import Any

import pytest
from conftest import FakeResult, FakeScalarsResult, FakeSession

from app.core.exceptions import NotFoundError
from app.models.deal import Deal
from app.models.stakeholder import Stakeholder
from app.schemas.stakeholder import StakeholderCreate
from app.services.stakeholder import service as stakeholder_svc


class StakeholderSession(FakeSession):
    """Session stub for stakeholder operations.

    Pass a sequence of results that will be returned in order by execute().
    """

    def __init__(self, results: list[Any] | None = None) -> None:
        super().__init__()
        self._results = iter(results or [])

    async def execute(self, stmt: object) -> Any:
        return next(self._results)


@pytest.mark.asyncio
async def test_create_stakeholder_verifies_deal_access() -> None:
    deal = Deal(
        id=uuid.uuid4(),
        org_id=uuid.uuid4(),
        name="D",
        account_name="A",
        stage="discovery",
    )
    # create_stakeholder: 1st call = deal check (returns deal id)
    session = StakeholderSession(results=[
        FakeResult(deal.id),
    ])
    payload = StakeholderCreate(name="Jane Doe")

    sh = await stakeholder_svc.create_stakeholder(
        session, deal.org_id, deal.id, payload  # type: ignore[arg-type]
    )

    assert sh.name == "Jane Doe"
    assert sh.deal_id == deal.id
    assert len(session.added) == 1


@pytest.mark.asyncio
async def test_create_stakeholder_rejects_wrong_org() -> None:
    # deal check returns None → NotFoundError
    session = StakeholderSession(results=[
        FakeResult(None),
    ])
    payload = StakeholderCreate(name="Jane Doe")

    with pytest.raises(NotFoundError):
        await stakeholder_svc.create_stakeholder(
            session, uuid.uuid4(), uuid.uuid4(), payload  # type: ignore[arg-type]
        )


@pytest.mark.asyncio
async def test_list_stakeholders_returns_deal_stakeholders() -> None:
    deal = Deal(
        id=uuid.uuid4(),
        org_id=uuid.uuid4(),
        name="D",
        account_name="A",
        stage="discovery",
    )
    sh = Stakeholder(
        id=uuid.uuid4(),
        deal_id=deal.id,
        name="Marcus",
        source_type="manual",
    )
    # list_stakeholders: single JOIN query returning stakeholders
    session = StakeholderSession(results=[
        FakeScalarsResult([sh]),
    ])

    result = await stakeholder_svc.list_stakeholders(
        session, deal.org_id, deal.id  # type: ignore[arg-type]
    )

    assert len(result) == 1
    assert result[0].name == "Marcus"
