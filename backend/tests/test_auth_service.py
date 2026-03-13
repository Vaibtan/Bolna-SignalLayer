"""Unit tests for authentication service behavior."""

from typing import Any

import pytest
from conftest import FakeRedis, FakeSession, build_user

from app.api.auth import get_client_ip
from app.api.deps import require_admin
from app.core.config import get_settings
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    RateLimitError,
)
from app.services.auth import service as auth_service


def build_request(
    client_ip: str,
    *,
    forwarded_for: str | None = None,
    real_ip: str | None = None,
) -> Any:
    """Create a minimal Starlette request object."""
    from starlette.requests import Request

    headers: list[tuple[bytes, bytes]] = []
    if forwarded_for is not None:
        headers.append((b'x-forwarded-for', forwarded_for.encode()))
    if real_ip is not None:
        headers.append((b'x-real-ip', real_ip.encode()))

    return Request(
        {
            'type': 'http',
            'method': 'POST',
            'path': '/api/auth/login',
            'query_string': b'',
            'headers': headers,
            'client': (client_ip, 1234),
            'server': ('testserver', 80),
            'scheme': 'http',
            'root_path': '',
            'http_version': '1.1',
        }
    )


@pytest.mark.asyncio
async def test_authenticate_user_clears_only_matching_email_ip_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis = FakeRedis()
    matching_key = auth_service._rate_limit_key(
        'admin@example.com',
        '203.0.113.10',
    )
    other_key = auth_service._rate_limit_key(
        'other@example.com',
        '203.0.113.10',
    )
    redis.store[matching_key] = '2'
    redis.store[other_key] = '4'

    monkeypatch.setattr(auth_service, 'get_redis_client', lambda: redis)
    monkeypatch.setattr(
        auth_service,
        'create_access_token',
        lambda *_args: 'signed-token',
    )

    user = build_user('admin@example.com', password='secret')
    token, authenticated_user = await auth_service.authenticate_user(
        FakeSession(user),
        'Admin@Example.com',
        'secret',
        '203.0.113.10',
    )

    assert token == 'signed-token'
    assert authenticated_user.email == 'admin@example.com'
    assert matching_key not in redis.store
    assert redis.store[other_key] == '4'


@pytest.mark.asyncio
async def test_authenticate_user_rate_limit_is_scoped_to_email_and_ip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis = FakeRedis()
    blocked_key = auth_service._rate_limit_key(
        'admin@example.com',
        '203.0.113.10',
    )
    redis.store[blocked_key] = str(get_settings().AUTH_MAX_FAILED_ATTEMPTS)
    redis.ttls[blocked_key] = 42

    monkeypatch.setattr(auth_service, 'get_redis_client', lambda: redis)

    with pytest.raises(RateLimitError) as blocked:
        await auth_service.authenticate_user(
            FakeSession(None),
            'admin@example.com',
            'secret',
            '203.0.113.10',
        )

    assert blocked.value.retry_after == 42

    with pytest.raises(AuthenticationError):
        await auth_service.authenticate_user(
            FakeSession(None),
            'other@example.com',
            'secret',
            '203.0.113.10',
        )


def test_get_client_ip_prefers_forwarded_headers_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv('TRUST_PROXY_HEADERS', 'true')
    get_settings.cache_clear()

    request = build_request(
        '10.0.0.10',
        forwarded_for='198.51.100.25, 10.0.0.10',
    )

    assert get_client_ip(request) == '198.51.100.25'

    get_settings.cache_clear()


def test_get_client_ip_uses_direct_client_when_proxy_headers_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv('TRUST_PROXY_HEADERS', 'false')
    get_settings.cache_clear()

    request = build_request(
        '10.0.0.10',
        forwarded_for='198.51.100.25, 10.0.0.10',
    )

    assert get_client_ip(request) == '10.0.0.10'

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_require_admin_raises_for_non_admin_user() -> None:
    operator = build_user('operator@example.com', role='operator')

    with pytest.raises(AuthorizationError):
        await require_admin(operator)
