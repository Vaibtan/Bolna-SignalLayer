"""Helpers for capturing real Bolna payloads as local fixtures."""

import json
from pathlib import Path
from typing import Any

import structlog

from app.core.config import get_settings

logger = structlog.get_logger(__name__)

_FILENAMES = {
    "webhook": "bolna_webhook_real.json",
    "polling": "bolna_execution_polling_real.json",
}


def maybe_capture_payload(
    payload: dict[str, Any],
    source: str,
) -> None:
    """Persist the first real provider payload for a given source."""
    settings = get_settings()
    if not settings.BOLNA_CAPTURE_REAL_PAYLOADS:
        return
    if payload.get("mock"):
        return

    filename = _FILENAMES.get(source)
    if filename is None:
        return

    target = Path(settings.BOLNA_CAPTURE_FIXTURES_DIR) / filename
    if target.exists():
        return

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        logger.info(
            "bolna.fixture_captured",
            source=source,
            path=str(target),
        )
    except Exception:
        logger.warning(
            "bolna.fixture_capture_failed",
            source=source,
            path=str(target),
            exc_info=True,
        )
