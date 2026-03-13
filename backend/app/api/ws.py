"""WebSocket endpoints for realtime updates."""

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.redis import get_redis_client
from app.core.security import decode_access_token
from app.db.session import get_session_factory
from app.models.call_session import CallSession
from app.models.deal import Deal
from app.services.realtime.pubsub import call_channel, deal_channel

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["websocket"])


def _authenticate_ws(websocket: WebSocket) -> dict[str, object] | None:
    """Validate JWT from cookie. Returns claims or None.

    Cannot reuse ``deps.get_current_user`` because the WS
    handshake must reject before ``accept()``.
    """
    token = websocket.cookies.get("access_token")
    if not token:
        return None
    try:
        return decode_access_token(token)
    except Exception:
        return None


async def _relay_pubsub(
    websocket: WebSocket,
    channel: str,
) -> None:
    """Subscribe to a Redis pub/sub channel and relay to the WebSocket.

    Uses the shared Redis client for the subscription context
    and cleans up the subscription on disconnect.
    """
    redis = get_redis_client()
    pubsub = redis.pubsub()
    await pubsub.subscribe(channel)

    async def _forward() -> None:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])

    async def _wait_disconnect() -> None:
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass

    forward_task = asyncio.create_task(_forward())
    disconnect_task = asyncio.create_task(_wait_disconnect())

    try:
        _done, pending = await asyncio.wait(
            [forward_task, disconnect_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()


async def _ws_endpoint(
    websocket: WebSocket,
    channel: str,
    authorize: Callable[[str], Awaitable[bool]],
    log_ctx: dict[str, Any],
) -> None:
    """Shared WebSocket lifecycle: auth, authorize, accept, relay."""
    claims = _authenticate_ws(websocket)
    if claims is None:
        await websocket.close(code=4001)
        return

    org_id = str(claims.get("org", ""))
    if not org_id or not await authorize(org_id):
        await websocket.close(code=4003)
        return

    await websocket.accept()
    logger.info("ws.connected", **log_ctx)

    try:
        await _relay_pubsub(websocket, channel)
    except Exception:
        logger.debug("ws.disconnected", **log_ctx)


@router.websocket("/ws/calls/{call_id}")
async def ws_call(
    websocket: WebSocket,
    call_id: uuid.UUID,
) -> None:
    """WebSocket endpoint for call status updates."""

    async def authorize(org_id: str) -> bool:
        async with get_session_factory()() as db:
            row = await db.execute(
                select(CallSession.id)
                .join(Deal, Deal.id == CallSession.deal_id)
                .where(
                    CallSession.id == call_id,
                    Deal.org_id == uuid.UUID(org_id),
                )
            )
            return row.scalar_one_or_none() is not None

    await _ws_endpoint(
        websocket,
        call_channel(str(call_id)),
        authorize,
        {"call_id": str(call_id)},
    )


@router.websocket("/ws/deals/{deal_id}")
async def ws_deal(
    websocket: WebSocket,
    deal_id: uuid.UUID,
) -> None:
    """WebSocket endpoint for deal-level updates."""

    async def authorize(org_id: str) -> bool:
        async with get_session_factory()() as db:
            row = await db.execute(
                select(Deal.id).where(
                    Deal.id == deal_id,
                    Deal.org_id == uuid.UUID(org_id),
                )
            )
            return row.scalar_one_or_none() is not None

    await _ws_endpoint(
        websocket,
        deal_channel(str(deal_id)),
        authorize,
        {"deal_id": str(deal_id)},
    )
