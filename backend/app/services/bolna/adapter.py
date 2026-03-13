"""Bolna provider adapter interface and implementations."""

from __future__ import annotations

import abc
import uuid
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import httpx
import structlog

from app.core.config import get_settings

logger = structlog.get_logger(__name__)


@dataclass
class CallRequest:
    """Data required to initiate a Bolna outbound call."""

    agent_id: str
    recipient_phone_number: str
    user_data: dict[str, Any]


@dataclass
class CallResponse:
    """Result returned by the provider after call initiation."""

    provider_call_id: str
    raw_response: dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error_message: str | None = None


class BolnaAdapter(abc.ABC):
    """Abstract adapter for the Bolna voice provider."""

    @abc.abstractmethod
    async def initiate_call(
        self, request: CallRequest,
    ) -> CallResponse:
        """Start an outbound call and return the provider response."""

    @abc.abstractmethod
    async def get_execution(
        self, execution_id: str,
    ) -> dict[str, Any]:
        """Fetch execution status from the provider."""


class BolnaHttpAdapter(BolnaAdapter):
    """Real Bolna adapter that calls the Bolna API over HTTP."""

    _BASE_URL = "https://api.bolna.ai"

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.BOLNA_API_KEY
        self._client = httpx.AsyncClient(
            base_url=self._BASE_URL,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(30.0),
        )

    async def initiate_call(
        self, request: CallRequest,
    ) -> CallResponse:
        """POST to Bolna /call endpoint."""
        payload = {
            "agent_id": request.agent_id,
            "recipient_phone_number": (
                request.recipient_phone_number
            ),
            "user_data": request.user_data,
        }

        try:
            resp = await self._client.post(
                "/call", json=payload,
            )
        except httpx.HTTPError as exc:
            logger.error(
                "bolna.call_error", error=str(exc),
            )
            return CallResponse(
                provider_call_id="",
                raw_response={},
                success=False,
                error_message=(
                    f"Bolna connection error: {exc}"
                ),
            )

        # Parse JSON defensively — Bolna may return
        # non-JSON bodies on certain error codes.
        try:
            body: dict[str, Any] = resp.json()
        except Exception:
            body = {}

        if resp.status_code == 429:
            logger.warning(
                "bolna.rate_limited",
                status=resp.status_code,
            )
            return CallResponse(
                provider_call_id="",
                raw_response=body,
                success=False,
                error_message="Bolna rate limit exceeded.",
            )

        if not resp.is_success:
            logger.error(
                "bolna.call_failed",
                status=resp.status_code,
                body=resp.text,
            )
            return CallResponse(
                provider_call_id="",
                raw_response=body or {
                    "error": resp.text,
                },
                success=False,
                error_message=(
                    f"Bolna API error: {resp.status_code}"
                ),
            )

        # Validate that a usable execution ID exists.
        provider_call_id = (
            body.get("execution_id")
            or body.get("id")
            or ""
        )
        if not provider_call_id:
            logger.warning(
                "bolna.missing_execution_id",
                status=resp.status_code,
                body=body,
            )
            return CallResponse(
                provider_call_id="",
                raw_response=body,
                success=False,
                error_message=(
                    "Bolna returned no execution ID."
                ),
            )

        logger.info(
            "bolna.call_initiated",
            provider_call_id=provider_call_id,
        )
        return CallResponse(
            provider_call_id=str(provider_call_id),
            raw_response=body,
        )


    async def get_execution(
        self, execution_id: str,
    ) -> dict[str, Any]:
        """GET /executions/{execution_id}."""
        try:
            resp = await self._client.get(
                f"/executions/{execution_id}",
            )
        except httpx.HTTPError as exc:
            logger.error(
                "bolna.poll_error", error=str(exc),
            )
            return {"error": str(exc)}

        try:
            return resp.json()  # type: ignore[no-any-return]
        except Exception:
            return {"error": resp.text}


class BolnaMockAdapter(BolnaAdapter):
    """Mock adapter for local development and testing."""

    async def initiate_call(
        self, request: CallRequest,
    ) -> CallResponse:
        """Return a synthetic call ID without real call."""
        mock_id = f"mock-{uuid.uuid4().hex[:12]}"
        logger.info(
            "bolna.mock_call_initiated",
            provider_call_id=mock_id,
            phone=request.recipient_phone_number,
        )
        return CallResponse(
            provider_call_id=mock_id,
            raw_response={
                "execution_id": mock_id,
                "status": "queued",
                "mock": True,
            },
        )


    async def get_execution(
        self, execution_id: str,
    ) -> dict[str, Any]:
        """Return a synthetic completed execution."""
        return {
            "execution_id": execution_id,
            "status": "completed",
            "transcript": "Mock transcript.",
            "duration": 42,
            "recording_url": f"https://mock/{execution_id}.wav",
            "mock": True,
        }


@lru_cache(maxsize=1)
def get_bolna_adapter() -> BolnaAdapter:
    """Return a singleton Bolna adapter based on config."""
    settings = get_settings()
    if settings.BOLNA_MOCK_MODE:
        return BolnaMockAdapter()
    return BolnaHttpAdapter()


async def close_bolna_adapter() -> None:
    """Close the cached HTTP adapter client if it has been created."""
    if get_bolna_adapter.cache_info().currsize == 0:
        return

    adapter = get_bolna_adapter()
    if isinstance(adapter, BolnaHttpAdapter):
        await adapter._client.aclose()
    get_bolna_adapter.cache_clear()
