"""Shared test configuration and fixtures."""

import json
import uuid
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, cast

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import hash_password
from app.main import app
from app.models.user import User

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict[str, Any]:
    """Load a JSON test fixture by filename."""
    return cast(
        dict[str, Any],
        json.loads((FIXTURES / name).read_text()),
    )


def pytest_configure(config: pytest.Config) -> None:
    import os

    os.environ["DATABASE_URL"] = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/signal_layer_test"
    )
    os.environ["REDIS_URL"] = "redis://localhost:6379/1"
    os.environ["JWT_SECRET"] = "testsecret"
    os.environ["ENVIRONMENT"] = "test"


class FakePipeline:
    """Minimal Redis pipeline stub."""

    def __init__(self, redis: 'FakeRedis') -> None:
        self.redis = redis
        self.operations: list[tuple[str, Any]] = []

    def incr(self, key: str) -> 'FakePipeline':
        self.operations.append(('incr', key))
        return self

    def expire(self, key: str, ttl: int) -> 'FakePipeline':
        self.operations.append(('expire', (key, ttl)))
        return self

    async def execute(self) -> list[object]:
        results: list[object] = []
        for operation, value in self.operations:
            if operation == 'incr':
                key = value
                current = int(self.redis.store.get(key, '0'))
                new_val = current + 1
                self.redis.store[key] = str(new_val)
                results.append(new_val)
            elif operation == 'expire':
                key, ttl = value
                self.redis.ttls[key] = ttl
                results.append(True)
        return results


class FakeRedis:
    """In-memory async Redis stub."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def ttl(self, key: str) -> int:
        return self.ttls.get(key, -1)

    async def set(
        self,
        key: str,
        value: str,
        nx: bool = False,
        ex: int | None = None,
    ) -> bool | None:
        if nx and key in self.store:
            return False
        self.store[key] = value
        if ex is not None:
            self.ttls[key] = ex
        return True

    async def decr(self, key: str) -> int:
        current = int(self.store.get(key, '0'))
        next_value = current - 1
        self.store[key] = str(next_value)
        return next_value

    async def delete(self, key: str) -> None:
        self.store.pop(key, None)
        self.ttls.pop(key, None)

    def pipeline(self) -> FakePipeline:
        return FakePipeline(self)


class FakeResult:
    """Simple SQLAlchemy result stub."""

    def __init__(self, value: object | None) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object | None:
        return self._value

    def scalar_one(self) -> object:
        if self._value is None:
            raise AssertionError('Expected a scalar value, got None.')
        return self._value


class FakeScalarsResult:
    """Stub for select() results with scalars().all() chain."""

    def __init__(self, items: list[Any]) -> None:
        self._items = items

    def scalar_one_or_none(self) -> Any:
        return self._items[0] if self._items else None

    def scalars(self) -> 'FakeScalarsResult':
        return self

    def all(self) -> list[Any]:
        return self._items


class FakeSession:
    """Minimal async session stub.

    Supports both simple lookup (pass a return value) and seed-style
    tracking (add, flush, commit).
    """

    def __init__(self, return_value: object | None = None) -> None:
        self._return_value = return_value
        self.added: list[Any] = []
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> 'FakeSession':
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def execute(self, _query: object) -> FakeResult:
        return FakeResult(self._return_value)

    def add(self, instance: Any) -> None:
        self.added.append(instance)

    @asynccontextmanager
    async def begin_nested(self) -> AsyncIterator['FakeSession']:
        yield self

    async def flush(self) -> None:
        if self.added:
            self.added[0].id = object()

    async def commit(self) -> None:
        self.committed = True

    async def refresh(self, _instance: Any) -> None:
        pass

    async def rollback(self) -> None:
        self.rolled_back = True


def build_user(
    email: str = 'admin@example.com',
    password: str | None = None,
    role: str = 'admin',
    name: str = 'Test User',
) -> User:
    """Create a detached User model for tests."""
    return User(
        id=uuid.uuid4(),
        org_id=uuid.uuid4(),
        name=name,
        email=email,
        password_hash=hash_password(password) if password else 'unused',
        role=role,
    )


async def override_db() -> AsyncIterator[FakeSession]:
    """Provide a dummy DB dependency for route tests."""
    yield FakeSession()


@pytest.fixture(autouse=True)
def _clear_dependency_overrides() -> Iterator[None]:
    """Guarantee app dependency overrides are cleaned up after every test."""
    yield
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Yield an httpx AsyncClient wired to the FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url='http://test',
    ) as ac:
        yield ac
