"""Manual smoke test for validating a real outbound Bolna call."""

from __future__ import annotations

import argparse
import asyncio
import os

from app.core.config import get_settings
from app.services.bolna.adapter import CallRequest, get_bolna_adapter


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Place a real Bolna call to validate live outbound flow.",
    )
    parser.add_argument(
        "--phone",
        default=os.getenv("BOLNA_SMOKE_TEST_NUMBER", ""),
        help="Destination phone number for the smoke test call.",
    )
    parser.add_argument(
        "--objective",
        default="discovery_qualification",
        help="Call objective to send in user_data.",
    )
    parser.add_argument(
        "--topics",
        default="Confirm availability and validate procurement timeline.",
        help="Optional topic notes passed to Bolna.",
    )
    return parser.parse_args()


async def _main() -> int:
    args = _parse_args()
    settings = get_settings()
    if settings.BOLNA_MOCK_MODE:
        print("BOLNA_MOCK_MODE=true; disable mock mode for live validation.")
        return 1
    if not settings.BOLNA_API_KEY or not settings.BOLNA_AGENT_ID:
        print("Missing BOLNA_API_KEY or BOLNA_AGENT_ID.")
        return 1
    if not args.phone:
        print("Provide --phone or set BOLNA_SMOKE_TEST_NUMBER.")
        return 1

    adapter = get_bolna_adapter()
    response = await adapter.initiate_call(
        CallRequest(
            agent_id=settings.BOLNA_AGENT_ID,
            recipient_phone_number=args.phone,
            user_data={
                "stakeholder_name": "Smoke Test Contact",
                "stakeholder_title": "Test Contact",
                "company_name": "Signal Layer OS Smoke Test",
                "deal_context": (
                    "This is a manual smoke test call to validate the live "
                    "Bolna integration and webhook flow."
                ),
                "call_objective": args.objective,
                "open_questions": [args.topics],
            },
        )
    )

    if response.success:
        print("Live call initiated successfully.")
        print(f"Execution ID: {response.provider_call_id}")
        print(
            "If BOLNA_CAPTURE_REAL_PAYLOADS=true, the first real webhook and "
            "polling payloads will be written to the configured capture dir."
        )
        return 0

    print("Live call initiation failed.")
    print(response.error_message or "Unknown Bolna error.")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
