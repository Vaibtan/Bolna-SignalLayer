"""Route tests for Phase 2 authentication endpoints."""

import pytest
from conftest import build_user, override_db
from httpx import AsyncClient

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.exceptions import RateLimitError
from app.main import app


@pytest.mark.asyncio
async def test_login_sets_cookie(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
) -> None:
    from app.api import auth as auth_api
    from app.db.session import get_db_session

    async def fake_authenticate_user(*_args: object) -> tuple[str, object]:
        return 'signed-token', object()

    monkeypatch.setenv('AUTH_COOKIE_SECURE', 'true')
    get_settings.cache_clear()
    monkeypatch.setattr(auth_api, 'authenticate_user', fake_authenticate_user)
    app.dependency_overrides[get_db_session] = override_db

    response = await client.post(
        '/api/auth/login',
        json={
            'email': 'admin@example.com',
            'password': 'secret',
        },
    )

    assert response.status_code == 200
    assert response.json() == {'token_type': 'bearer'}
    set_cookie = response.headers['set-cookie']
    assert 'access_token=signed-token' in set_cookie
    assert 'HttpOnly' in set_cookie
    assert 'Secure' in set_cookie

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_login_rate_limit_returns_retry_after_header(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
) -> None:
    from app.api import auth as auth_api
    from app.db.session import get_db_session

    async def fake_authenticate_user(*_args: object) -> tuple[str, object]:
        raise RateLimitError(retry_after=33)

    monkeypatch.setattr(auth_api, 'authenticate_user', fake_authenticate_user)
    app.dependency_overrides[get_db_session] = override_db

    response = await client.post(
        '/api/auth/login',
        json={
            'email': 'admin@example.com',
            'password': 'secret',
        },
    )

    assert response.status_code == 429
    assert response.headers['Retry-After'] == '33'



@pytest.mark.asyncio
async def test_me_returns_authenticated_user(
    client: AsyncClient,
) -> None:
    user = build_user()

    async def fake_current_user() -> object:
        return user

    app.dependency_overrides[get_current_user] = fake_current_user

    response = await client.get('/api/auth/me')

    assert response.status_code == 200
    assert response.json()['email'] == 'admin@example.com'
    assert response.json()['role'] == 'admin'

