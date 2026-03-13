"""Tests for WebSocket endpoints."""

import uuid

import pytest
from conftest import FakeResult
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import app.api.ws as ws_module
from app.core.security import create_access_token
from app.main import app


def _make_token(
    org_id: uuid.UUID | None = None,
) -> tuple[str, uuid.UUID]:
    """Create a valid JWT. Returns (token, org_id)."""
    oid = org_id or uuid.uuid4()
    token = create_access_token(
        user_id=uuid.uuid4(),
        org_id=oid,
        role="admin",
    )
    return token, oid


class _AuthorizeSession:
    """DB session stub that returns a given value for any query."""

    def __init__(self, result: object) -> None:
        self._result = result

    async def __aenter__(self) -> "_AuthorizeSession":
        return self

    async def __aexit__(self, *_a: object) -> None:
        return None

    async def execute(self, _stmt: object) -> FakeResult:
        return FakeResult(self._result)


@pytest.mark.parametrize(
    "url_prefix", ["/ws/calls/", "/ws/deals/"],
)
def test_ws_rejects_without_auth(url_prefix: str) -> None:
    """WebSocket connection without a cookie is closed."""
    client = TestClient(app)
    resource_id = str(uuid.uuid4())

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            f"{url_prefix}{resource_id}",
        ):
            pass


@pytest.mark.parametrize(
    "url_prefix", ["/ws/calls/", "/ws/deals/"],
)
def test_ws_rejects_wrong_org(
    monkeypatch: pytest.MonkeyPatch,
    url_prefix: str,
) -> None:
    """WebSocket with valid JWT but resource from another org is rejected."""
    token, _ = _make_token()
    resource_id = str(uuid.uuid4())

    monkeypatch.setattr(
        ws_module,
        "get_session_factory",
        lambda: lambda: _AuthorizeSession(None),
    )

    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            f"{url_prefix}{resource_id}",
            cookies={"access_token": token},
        ):
            pass


@pytest.mark.parametrize(
    "url_prefix", ["/ws/calls/", "/ws/deals/"],
)
def test_ws_accepts_with_matching_org(
    monkeypatch: pytest.MonkeyPatch,
    url_prefix: str,
) -> None:
    """WebSocket with valid JWT and matching org is accepted."""
    resource_id = uuid.uuid4()
    token, _ = _make_token()

    monkeypatch.setattr(
        ws_module,
        "get_session_factory",
        lambda: lambda: _AuthorizeSession(resource_id),
    )

    client = TestClient(app)
    with client.websocket_connect(
        f"{url_prefix}{resource_id}",
        cookies={"access_token": token},
    ) as ws:
        ws.close()
