"""Periodic maintenance scheduler for low-frequency background jobs."""

from __future__ import annotations

import time

import structlog

from app.core.config import get_settings
from app.workers.tasks import sweep_transcript_retention

logger = structlog.get_logger(__name__)
_MIN_SWEEP_INTERVAL_SECONDS = 60


def main() -> None:
    """Enqueue periodic maintenance jobs on a fixed interval."""
    settings = get_settings()
    interval_seconds = max(
        settings.TRANSCRIPT_RETENTION_SWEEP_INTERVAL_SECONDS,
        _MIN_SWEEP_INTERVAL_SECONDS,
    )

    logger.info(
        "maintenance.scheduler_started",
        transcript_retention_interval_seconds=interval_seconds,
    )

    while True:
        try:
            sweep_transcript_retention.send()
            logger.info(
                "maintenance.transcript_retention_enqueued",
            )
        except Exception:
            logger.warning(
                "maintenance.transcript_retention_enqueue_failed",
                exc_info=True,
            )
        time.sleep(interval_seconds)


if __name__ == "__main__":
    main()
