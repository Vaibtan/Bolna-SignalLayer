"""Risk engine: extraction → snapshots → deal projections.

Acquires a row-level lock on the Deal before mutating
projections so concurrent call completions for the same
deal do not corrupt the latest state.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from app.models.call_session import CallSession
from app.models.deal import Deal
from app.models.deal_snapshot import DealSnapshot
from app.models.extraction_snapshot import ExtractionSnapshot
from app.models.risk_snapshot import RiskSnapshot
from app.models.stakeholder import Stakeholder
from app.models.stakeholder_snapshot import StakeholderSnapshot
from app.services.risk.scoring import risk_level, score_extraction

logger = structlog.get_logger(__name__)
_SNAPSHOTS_STALE_AFTER = timedelta(seconds=60)

_RISK_ELIGIBLE = frozenset({
    "extraction_completed",
    "failed_retryable",
})


class RetryableRiskError(Exception):
    """Raised when the risk pipeline should be retried."""


def _is_stale_snapshots_state(
    updated_at: datetime | None,
) -> bool:
    """Return whether a snapshots_updating state is stale enough to resume."""
    if updated_at is None:
        return True
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    return (
        datetime.now(timezone.utc) - updated_at
        >= _SNAPSHOTS_STALE_AFTER
    )


async def run_risk_update(
    db: AsyncSession,
    call_session_id: uuid.UUID,
) -> RiskSnapshot | None:
    """Compute risk after extraction completes.

    Transitions ``processing_status``:
      ``extraction_completed`` → ``snapshots_updating``
      → ``risk_running`` (terminal for now; Phase 10 chains).

    Returns the new risk snapshot, or None if skipped.
    """
    # 1. Claim the call session.
    row = await db.execute(
        select(CallSession)
        .where(CallSession.id == call_session_id)
        .with_for_update()
    )
    session = row.scalar_one_or_none()
    if session is None:
        await db.rollback()
        return None

    can_resume_stale = (
        session.processing_status == "snapshots_updating"
        and _is_stale_snapshots_state(session.updated_at)
    )
    if (
        session.processing_status not in _RISK_ELIGIBLE
        and not can_resume_stale
    ):
        logger.info(
            "risk.skipped",
            call_session_id=str(call_session_id),
            status=session.processing_status,
        )
        await db.rollback()
        return None

    await db.execute(
        update(CallSession)
        .where(CallSession.id == call_session_id)
        .values(
            processing_status="snapshots_updating",
            updated_at=func.now(),
        )
    )
    session.processing_status = "snapshots_updating"
    session.updated_at = datetime.now(timezone.utc)
    await db.commit()

    try:
        # 2. Lock the Deal row.
        deal_row = await db.execute(
            select(Deal)
            .where(Deal.id == session.deal_id)
            .with_for_update()
        )
        deal: Deal | None = deal_row.scalar_one_or_none()
        if deal is None:
            await db.rollback()
            logger.error(
                "risk.deal_not_found",
                deal_id=str(session.deal_id),
            )
            return None

        # 3. Load the latest extraction for this call.
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
        if extraction is None:
            logger.warning(
                "risk.no_extraction",
                call_session_id=str(call_session_id),
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
            raise RetryableRiskError(
                "Extraction artifact not available yet.",
            )

        extracted: dict[str, Any] = dict(extraction.extracted_json)

        # 4. Load stakeholders for coverage computation.
        sh_row = await db.execute(
            select(Stakeholder)
            .options(load_only(
                Stakeholder.id,
                Stakeholder.deal_id,
                Stakeholder.last_contacted_at,
            ))
            .where(Stakeholder.deal_id == deal.id)
        )
        stakeholders = list(sh_row.scalars().all())
        stakeholder_count = len(stakeholders)

        # 5. Load previous risk snapshot for delta.
        prev_row = await db.execute(
            select(RiskSnapshot)
            .where(RiskSnapshot.deal_id == deal.id)
            .order_by(RiskSnapshot.created_at.desc())
            .limit(1)
        )
        prev_snapshot = prev_row.scalar_one_or_none()

        # 6. Run deterministic scoring.
        score, factors = score_extraction(
            extracted, stakeholder_count,
        )
        level = risk_level(score)

        # 7. Compute change summary.
        change_summary: list[str] = []
        if prev_snapshot is not None:
            delta = score - prev_snapshot.score
            if delta > 0:
                change_summary.append(
                    f"Risk increased by {delta} points",
                )
            elif delta < 0:
                change_summary.append(
                    f"Risk decreased by {abs(delta)} points",
                )
            else:
                change_summary.append("Risk score unchanged")

            pf_raw = (
                prev_snapshot.factors_json or {}
            ).get("factors", [])
            prev_factors: list[str] = (
                list(pf_raw)
                if isinstance(pf_raw, list)
                else []
            )
            new_factors = set(factors) - set(prev_factors)
            for nf in new_factors:
                change_summary.append(f"New: {nf}")

        # 8. Update stakeholder projection from extraction.
        sh_extraction = extracted.get("stakeholder", {})
        interaction = extracted.get("interaction", {})
        target_sh = next(
            (
                s
                for s in stakeholders
                if s.id == session.stakeholder_id
            ),
            None,
        )
        if target_sh is not None:
            sh_updates: dict[str, Any] = {
                "last_contacted_at": func.now(),
                "updated_at": func.now(),
            }
            target_sh.last_contacted_at = datetime.now(
                timezone.utc,
            )
            if sh_extraction.get("role_label"):
                sh_updates["role_label_current"] = (
                    sh_extraction["role_label"]
                )
            if sh_extraction.get("role_confidence") is not None:
                sh_updates["role_confidence_current"] = (
                    sh_extraction["role_confidence"]
                )
            if interaction.get("sentiment"):
                sh_updates["sentiment_current"] = (
                    interaction["sentiment"]
                )
            await db.execute(
                update(Stakeholder)
                .where(Stakeholder.id == target_sh.id)
                .values(**sh_updates)
            )

            # Append-only stakeholder snapshot.
            db.add(
                StakeholderSnapshot(
                    stakeholder_id=target_sh.id,
                    summary=extraction.summary,
                    role_label=sh_extraction.get("role_label"),
                    role_confidence=sh_extraction.get(
                        "role_confidence",
                    ),
                    stance=None,
                    sentiment=interaction.get("sentiment"),
                )
            )

        # 9. Compute coverage status from the updated in-memory state.
        contacted = sum(
            1
            for s in stakeholders
            if s.last_contacted_at is not None
        )
        if stakeholder_count == 0:
            coverage = "none"
        elif contacted >= stakeholder_count:
            coverage = "full"
        elif contacted > 0:
            coverage = "partial"
        else:
            coverage = "none"

        # 10. Write deal snapshot.
        signals = extracted.get("deal_signals", {})
        db.add(
            DealSnapshot(
                deal_id=deal.id,
                summary=extraction.summary,
                coverage_status=coverage,
                key_signals_json=signals,
            )
        )

        # 11. Write risk snapshot.
        risk = RiskSnapshot(
            deal_id=deal.id,
            call_session_id=call_session_id,
            score=score,
            level=level,
            factors_json={"factors": factors},
            change_summary_json={"changes": change_summary},
        )
        db.add(risk)

        # 12. Update Deal projections.
        await db.execute(
            update(Deal)
            .where(Deal.id == deal.id)
            .values(
                risk_score_current=score,
                risk_level_current=level,
                coverage_status_current=coverage,
                summary_current=extraction.summary,
                updated_at=func.now(),
            )
        )

        # 13. Transition to risk_running (final for Phase 9).
        await db.execute(
            update(CallSession)
            .where(CallSession.id == call_session_id)
            .values(
                processing_status="risk_running",
                updated_at=func.now(),
            )
        )
        await db.commit()
    except RetryableRiskError:
        raise
    except Exception as exc:
        await db.rollback()
        logger.error(
            "risk.failed",
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
        raise RetryableRiskError(
            "Risk computation failed and should be retried.",
        ) from exc

    logger.info(
        "risk.completed",
        call_session_id=str(call_session_id),
        deal_id=str(deal.id),
        score=score,
        level=level,
        factor_count=len(factors),
    )
    return risk
