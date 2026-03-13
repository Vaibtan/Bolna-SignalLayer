"""Tests for the Phase 2 seed script."""

import pytest
from conftest import FakeResult, FakeSession

from scripts import seed as seed_script


class SeedSession(FakeSession):
    """Extended session stub that tracks execute calls for upsert."""

    def __init__(self) -> None:
        super().__init__()
        self.executed_statements: list[object] = []
        self._results = iter([
            "org-created",
            "user-created",
        ])

    async def execute(self, stmt: object) -> FakeResult:
        self.executed_statements.append(stmt)
        return FakeResult(next(self._results, None))


@pytest.mark.asyncio
async def test_seed_creates_org_and_admin_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = SeedSession()

    def fake_factory() -> object:
        return lambda: fake_session

    monkeypatch.setattr(seed_script, 'get_session_factory', fake_factory)

    await seed_script.seed()

    assert fake_session.added == []
    assert len(fake_session.executed_statements) == 2
    assert fake_session.committed is True
    assert fake_session.rolled_back is False


@pytest.mark.asyncio
async def test_seed_reuses_existing_org_when_upsert_does_not_insert(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = SeedSession()
    fake_session._results = iter([
        None,
        "existing-org-id",
        None,
    ])

    def fake_factory() -> object:
        return lambda: fake_session

    monkeypatch.setattr(seed_script, 'get_session_factory', fake_factory)

    await seed_script.seed()

    assert fake_session.added == []
    assert len(fake_session.executed_statements) == 3
    assert fake_session.committed is False
    assert fake_session.rolled_back is True


@pytest.mark.asyncio
async def test_seed_rolls_back_new_org_if_admin_user_already_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = SeedSession()
    fake_session._results = iter([
        "new-org-id",
        None,
    ])

    def fake_factory() -> object:
        return lambda: fake_session

    monkeypatch.setattr(seed_script, 'get_session_factory', fake_factory)

    await seed_script.seed()

    assert len(fake_session.executed_statements) == 2
    assert fake_session.committed is False
    assert fake_session.rolled_back is True
