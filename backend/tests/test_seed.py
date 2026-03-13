"""Tests for the seed script."""

import pytest
from conftest import FakeResult, FakeSession

from scripts import seed as seed_script


class SeedSession(FakeSession):
    """Extended session stub that tracks execute calls for upsert."""

    def __init__(self) -> None:
        super().__init__()
        self.executed_statements: list[object] = []
        self._results = iter([
            None,                # advisory lock
            "org-created",       # org upsert returning id
            "user-created",      # user upsert returning id
            None,                # deal exists check → None (not found)
        ])

    async def execute(self, stmt: object) -> FakeResult:
        self.executed_statements.append(stmt)
        return FakeResult(next(self._results, None))


@pytest.mark.asyncio
async def test_seed_creates_org_admin_deal_and_stakeholders(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = SeedSession()

    def fake_factory() -> object:
        return lambda: fake_session

    monkeypatch.setattr(seed_script, 'get_session_factory', fake_factory)

    await seed_script.seed()

    # 4 execute calls: lock, org upsert, user upsert, deal exists check
    assert len(fake_session.executed_statements) == 4
    # 1 deal + 3 stakeholders added via session.add
    assert len(fake_session.added) == 4
    assert fake_session.committed is True
    assert fake_session.rolled_back is False


@pytest.mark.asyncio
async def test_seed_reuses_existing_org_and_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = SeedSession()
    fake_session._results = iter([
        None,                # advisory lock
        None,                # org upsert → conflict, no id returned
        "existing-org-id",   # select existing org
        None,                # user upsert → conflict, no id returned
        "existing-user-id",  # select existing user
        None,                # deal exists check → None (not found)
    ])

    def fake_factory() -> object:
        return lambda: fake_session

    monkeypatch.setattr(seed_script, 'get_session_factory', fake_factory)

    await seed_script.seed()

    assert len(fake_session.executed_statements) == 6
    # Deal + 3 stakeholders
    assert len(fake_session.added) == 4
    assert fake_session.committed is True


@pytest.mark.asyncio
async def test_seed_skips_when_deal_already_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = SeedSession()
    fake_session._results = iter([
        None,                # advisory lock
        "org-id",            # org upsert
        "user-id",           # user upsert
        "existing-deal-id",  # deal exists check → found
    ])

    def fake_factory() -> object:
        return lambda: fake_session

    monkeypatch.setattr(seed_script, 'get_session_factory', fake_factory)

    await seed_script.seed()

    assert len(fake_session.executed_statements) == 4
    assert fake_session.added == []
    assert fake_session.committed is True
    assert fake_session.rolled_back is False
