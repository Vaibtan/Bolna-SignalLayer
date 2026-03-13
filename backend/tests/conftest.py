"""Shared test configuration and fixtures."""

import uuid
from collections.abc import AsyncIterator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import hash_password
from app.main import app
from app.models.user import User


def pytest_configure(config: pytest.Config) -> None:
    import os

    os.environ["DATABASE_URL"] = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/dealgraph_test"
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

    async def execute(self) -> None:
        for operation, value in self.operations:
            if operation == 'incr':
                key = value
                current = int(self.redis.store.get(key, '0'))
                self.redis.store[key] = str(current + 1)
            elif operation == 'expire':
                key, ttl = value
                self.redis.ttls[key] = ttl


class FakeRedis:
    """In-memory async Redis stub."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def ttl(self, key: str) -> int:
        return self.ttls.get(key, -1)

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

    async def flush(self) -> None:
        if self.added:
            self.added[0].id = object()

    async def commit(self) -> None:
        self.committed = True

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


async def override_db() -> AsyncIterator[object]:
    """Provide a dummy DB dependency for route tests."""
    yield object()


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Yield an httpx AsyncClient wired to the FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url='http://test',
    ) as ac:
        yield ac
