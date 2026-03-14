"""Recommendation pipeline: extraction + risk → actions + drafts.

Uses Gemini (gemini-2.5-pro) to generate next-best-action
recommendations and follow-up drafts including a CRM note.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from google import genai
from pydantic import ValidationError
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.action_recommendation import ActionRecommendation
from app.models.call_session import CallSession
from app.models.deal import Deal
from app.models.extraction_snapshot import ExtractionSnapshot
from app.models.followup_draft import FollowupDraft
from app.models.risk_snapshot import RiskSnapshot
from app.models.stakeholder import Stakeholder
from app.services.recommendation.schema import (
    PROMPT_VERSION,
    SCHEMA_VERSION,
    RecommendationOutput,
)

logger = structlog.get_logger(__name__)

_RECOMMENDATION_STALE_AFTER = timedelta(seconds=60)
_REC_ELIGIBLE = frozenset({
    "risk_running",
    "failed_retryable",
})

_RECOMMENDATION_PROMPT = """\
You are a B2B sales intelligence advisor. Based on the \
following call analysis, generate actionable next-best-action \
recommendations and follow-up drafts.

Rules:
- Provide 1-3 concrete, actionable recommendations.
- Each recommendation must explain WHY it matters now.
- Always generate at least one draft with draft_type "crm_note" \
  (a plain-text CRM-ready summary the user can paste into \
  Salesforce or HubSpot).
- If a follow-up email is warranted, include a draft with \
  draft_type "email" and a subject line.
- Prefer concrete actions over generic advice.
- Reference the specific deal context and risk factors.

Deal: {deal_name} ({account_name}, {stage} stage)
Deal Summary: {deal_summary}

Call Summary: {call_summary}

Extraction:
{extraction_json}

Risk Score: {risk_score}/100 ({risk_level})
Risk Factors: {risk_factors}

Stakeholders: {stakeholder_names}
"""


class RetryableRecommendationError(Exception):
    """Raised when recommendation generation should be retried."""


def _is_stale_recommendation_state(
    updated_at: datetime | None,
) -> bool:
    """Return whether a recommendation_running claim is stale."""
    if updated_at is None:
        return True
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    return (
        datetime.now(timezone.utc) - updated_at
        >= _RECOMMENDATION_STALE_AFTER
    )


def _build_prompt(
    deal: Deal,
    extraction: ExtractionSnapshot,
    risk: RiskSnapshot,
    stakeholders: list[Stakeholder],
) -> str:
    """Build the recommendation prompt from context."""
    extracted: dict[str, Any] = dict(extraction.extracted_json)
    raw_factors = (risk.factors_json or {}).get("factors", [])
    factors: list[str] = (
        list(raw_factors) if isinstance(raw_factors, list) else []
    )

    return _RECOMMENDATION_PROMPT.format(
        deal_name=deal.name,
        account_name=deal.account_name,
        stage=deal.stage or "unknown",
        deal_summary=deal.summary_current or "No summary.",
        call_summary=extraction.summary or "No summary.",
        extraction_json=str(extracted),
        risk_score=risk.score,
        risk_level=risk.level,
        risk_factors=", ".join(
            str(f) for f in factors
        ) if factors else "None",
        stakeholder_names=", ".join(
            s.name for s in stakeholders
        ) or "None",
    )


async def run_recommendation(
    db: AsyncSession,
    call_session_id: uuid.UUID,
) -> list[ActionRecommendation]:
    """Generate recommendations and drafts after risk.

    Transitions ``processing_status``:
      ``risk_running`` → ``recommendation_completed``.
    """
    settings = get_settings()

    # 1. Claim the call session.
    row = await db.execute(
        select(CallSession)
        .where(CallSession.id == call_session_id)
        .with_for_update()
    )
    session = row.scalar_one_or_none()
    if session is None:
        await db.rollback()
        return []

    can_resume_stale = (
        session.processing_status
        == "recommendation_running"
        and _is_stale_recommendation_state(
            session.updated_at,
        )
    )
    if (
        session.processing_status not in _REC_ELIGIBLE
        and not can_resume_stale
    ):
        logger.info(
            "recommendation.skipped",
            call_session_id=str(call_session_id),
            status=session.processing_status,
        )
        await db.rollback()
        return []

    await db.execute(
        update(CallSession)
        .where(CallSession.id == call_session_id)
        .values(
            processing_status="recommendation_running",
            updated_at=func.now(),
        )
    )
    session.processing_status = "recommendation_running"
    session.updated_at = datetime.now(timezone.utc)
    await db.commit()

    try:
        # 2. Load context.
        deal_row = await db.execute(
            select(Deal).where(Deal.id == session.deal_id)
        )
        deal = deal_row.scalar_one_or_none()
        if deal is None:
            await db.rollback()
            logger.error(
                "recommendation.deal_not_found",
                call_session_id=str(call_session_id),
                deal_id=str(session.deal_id),
            )
            return []

        ext_row = await db.execute(
            select(ExtractionSnapshot)
            .where(
                ExtractionSnapshot.call_session_id
                == call_session_id,
            )
            .order_by(ExtractionSnapshot.created_at.desc())
            .limit(1)
        )
        extraction = ext_row.scalar_one_or_none()

        risk_row = await db.execute(
            select(RiskSnapshot)
            .where(RiskSnapshot.deal_id == deal.id)
            .order_by(RiskSnapshot.created_at.desc())
            .limit(1)
        )
        risk = risk_row.scalar_one_or_none()

        if extraction is None or risk is None:
            logger.warning(
                "recommendation.missing_context",
                call_session_id=str(call_session_id),
                has_extraction=extraction is not None,
                has_risk=risk is not None,
            )
            await db.execute(
                update(CallSession)
                .where(CallSession.id == call_session_id)
                .values(
                    processing_status="failed_retryable",
                    updated_at=func.now(),
                )
            )
            await db.commit()
            raise RetryableRecommendationError(
                "Recommendation context not available yet.",
            )

        sh_row = await db.execute(
            select(Stakeholder).where(
                Stakeholder.deal_id == deal.id,
            )
        )
        stakeholders = list(sh_row.scalars().all())

        # 3. Call Gemini.
        prompt = _build_prompt(
            deal, extraction, risk, stakeholders,
        )
        client = genai.Client(
            api_key=settings.GEMINI_API_KEY,
        )

        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL_RECOMMENDATION,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_json_schema": (
                        RecommendationOutput.model_json_schema()
                    ),
                },
            )
            text = response.text or ""
            output = RecommendationOutput.model_validate_json(
                text,
            )
        except (ValidationError, Exception) as exc:
            logger.error(
                "recommendation.gemini_failed",
                call_session_id=str(call_session_id),
                error=str(exc),
            )
            output = _fallback_recommendation(
                extraction, risk,
            )

        # 4. Persist recommendations.
        recs: list[ActionRecommendation] = []
        target_sh = next(
            (
                stakeholder
                for stakeholder in stakeholders
                if stakeholder.id == session.stakeholder_id
            ),
            None,
        )
        for item in output.recommendations:
            rec = ActionRecommendation(
                deal_id=deal.id,
                call_session_id=call_session_id,
                target_stakeholder_id=(
                    target_sh.id if target_sh else None
                ),
                action_type=item.action_type,
                reason=item.reason,
                confidence=item.confidence,
                status="proposed",
                payload_json={
                    "talk_track": item.talk_track,
                    "schema_version": SCHEMA_VERSION,
                    "prompt_version": PROMPT_VERSION,
                    "model_name": (
                        settings.GEMINI_MODEL_RECOMMENDATION
                    ),
                },
            )
            db.add(rec)
            recs.append(rec)

        # 5. Persist drafts.
        for draft in output.drafts:
            db.add(
                FollowupDraft(
                    deal_id=deal.id,
                    call_session_id=call_session_id,
                    draft_type=draft.draft_type,
                    subject=draft.subject or None,
                    body_text=draft.body_text,
                    tone=draft.tone,
                    status="draft",
                )
            )

        # 6. Transition to recommendation_completed.
        await db.execute(
            update(CallSession)
            .where(CallSession.id == call_session_id)
            .values(
                processing_status="recommendation_completed",
                updated_at=func.now(),
            )
        )
        await db.commit()
    except RetryableRecommendationError:
        raise
    except Exception as exc:
        await db.rollback()
        logger.error(
            "recommendation.failed",
            call_session_id=str(call_session_id),
            error=str(exc),
        )
        await db.execute(
            update(CallSession)
            .where(CallSession.id == call_session_id)
            .values(
                processing_status="failed_retryable",
                updated_at=func.now(),
            )
        )
        await db.commit()
        raise RetryableRecommendationError(
            "Recommendation generation failed and should be retried.",
        ) from exc

    logger.info(
        "recommendation.completed",
        call_session_id=str(call_session_id),
        deal_id=str(deal.id),
        rec_count=len(recs),
        draft_count=len(output.drafts),
    )
    return recs


def _fallback_recommendation(
    extraction: ExtractionSnapshot,
    risk: RiskSnapshot,
) -> RecommendationOutput:
    """Generate a deterministic fallback when Gemini fails."""
    from app.services.recommendation.schema import (
        FollowupDraftItem,
        RecommendationItem,
    )

    raw_f = (risk.factors_json or {}).get("factors", [])
    factors: list[str] = (
        list(raw_f) if isinstance(raw_f, list) else []
    )
    summary = extraction.summary or "Call completed."

    if "No committed next step" in factors:
        action = RecommendationItem(
            action_type="send_followup",
            reason=(
                "No next step was agreed during the call. "
                "A follow-up email can re-establish momentum."
            ),
            confidence=0.7,
            talk_track=(
                "Reference specific topics discussed and "
                "propose a concrete next step with a date."
            ),
        )
    elif "No economic buyer identified" in factors:
        action = RecommendationItem(
            action_type="request_intro",
            reason=(
                "The economic buyer has not been identified. "
                "Ask the current contact for an introduction."
            ),
            confidence=0.6,
        )
    else:
        action = RecommendationItem(
            action_type="send_followup",
            reason="Follow up on the call to maintain momentum.",
            confidence=0.5,
        )

    crm_note = FollowupDraftItem(
        draft_type="crm_note",
        body_text=f"Call summary: {summary}",
        tone="professional",
    )

    return RecommendationOutput(
        recommendations=[action],
        drafts=[crm_note],
    )
