"""Webhook endpoints for provider callbacks."""

import json as json_mod
from typing import Any

import structlog
from fastapi import APIRouter, Request, Response

from app.api.deps import get_client_ip
from app.core.config import get_settings
from app.core.redis import get_redis_client
from app.db.session import get_session_factory
from app.services.bolna.ingestion import process_bolna_event

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/api/webhooks", tags=["webhooks"],
)


def _check_ip_allowlist(client_ip: str) -> bool:
    """Return True if the client IP is allowed."""
    settings = get_settings()
    allowed = settings.BOLNA_WEBHOOK_ALLOWED_IPS.strip()
    if not allowed:
        return True
    return client_ip in {
        ip.strip() for ip in allowed.split(",")
    }


@router.post("/bolna", status_code=200)
async def bolna_webhook(request: Request) -> Response:
    """Receive and process a Bolna provider webhook.

    Acknowledges with 200 after durable write regardless
    of downstream processing outcome.
    """
    client_ip = get_client_ip(request)
    if not _check_ip_allowlist(client_ip):
        logger.warning(
            "webhook.ip_rejected", ip=client_ip,
        )
        return Response(status_code=403)

    # Enforce payload size limit
    settings = get_settings()
    max_bytes = settings.WEBHOOK_MAX_BODY_SIZE_MB * 1024 * 1024
    body = await request.body()
    if len(body) > max_bytes:
        logger.warning(
            "webhook.payload_too_large",
            size=len(body),
        )
        return Response(status_code=413)

    try:
        parsed: Any = json_mod.loads(body)
    except (ValueError, TypeError):
        logger.warning("webhook.invalid_json")
        return Response(status_code=400)
    if not isinstance(parsed, dict):
        logger.warning("webhook.invalid_json_root")
        return Response(status_code=400)
    payload: dict[str, Any] = parsed

    redis = get_redis_client()
    session_factory = get_session_factory()

    async with session_factory() as db:
        processed = await process_bolna_event(
            db=db,
            redis=redis,
            raw_payload=payload,
            source="webhook",
        )

    logger.info(
        "webhook.bolna_handled",
        processed=processed,
        ip=client_ip,
        execution_id=payload.get("execution_id")
        or payload.get("id"),
        provider_status=payload.get("status"),
    )
    return Response(status_code=200)
