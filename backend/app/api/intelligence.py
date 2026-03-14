"""Intelligence API: recommendations, drafts, and risk."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import NotFoundError
from app.db.session import get_db_session
from app.models.action_recommendation import ActionRecommendation
from app.models.deal import Deal
from app.models.followup_draft import FollowupDraft
from app.models.risk_snapshot import RiskSnapshot
from app.models.user import User
from app.schemas.intelligence import (
    ActionRecommendationOut,
    FollowupDraftOut,
    RecommendationStatusUpdate,
    RiskSnapshotOut,
)

router = APIRouter(tags=["intelligence"])


async def _verify_deal_access(
    db: AsyncSession,
    deal_id: uuid.UUID,
    org_id: uuid.UUID,
) -> Deal:
    """Verify deal belongs to the user's org."""
    row = await db.execute(
        select(Deal).where(
            Deal.id == deal_id,
            Deal.org_id == org_id,
        )
    )
    deal = row.scalar_one_or_none()
    if deal is None:
        raise NotFoundError("Deal not found.")
    return deal


@router.get(
    "/api/deals/{deal_id}/recommendations",
    response_model=list[ActionRecommendationOut],
)
async def list_recommendations(
    deal_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[ActionRecommendationOut]:
    """List recommendations for a deal."""
    await _verify_deal_access(db, deal_id, current_user.org_id)
    result = await db.execute(
        select(ActionRecommendation)
        .where(ActionRecommendation.deal_id == deal_id)
        .order_by(ActionRecommendation.created_at.desc())
    )
    return [
        ActionRecommendationOut.model_validate(r)
        for r in result.scalars().all()
    ]


@router.post(
    "/api/recommendations/{recommendation_id}/accept",
    response_model=ActionRecommendationOut,
)
async def accept_recommendation(
    recommendation_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ActionRecommendationOut:
    """Accept a recommendation."""
    rec = await _get_recommendation(
        db, recommendation_id, current_user.org_id,
    )
    await db.execute(
        update(ActionRecommendation)
        .where(ActionRecommendation.id == recommendation_id)
        .values(status="accepted")
    )
    await db.commit()
    await db.refresh(rec)
    return ActionRecommendationOut.model_validate(rec)


@router.post(
    "/api/recommendations/{recommendation_id}/dismiss",
    response_model=ActionRecommendationOut,
)
async def dismiss_recommendation(
    recommendation_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ActionRecommendationOut:
    """Dismiss a recommendation."""
    rec = await _get_recommendation(
        db, recommendation_id, current_user.org_id,
    )
    await db.execute(
        update(ActionRecommendation)
        .where(ActionRecommendation.id == recommendation_id)
        .values(status="dismissed")
    )
    await db.commit()
    await db.refresh(rec)
    return ActionRecommendationOut.model_validate(rec)


@router.patch(
    "/api/recommendations/{recommendation_id}",
    response_model=ActionRecommendationOut,
)
async def update_recommendation(
    recommendation_id: uuid.UUID,
    payload: RecommendationStatusUpdate,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ActionRecommendationOut:
    """Update a recommendation's status or reason."""
    rec = await _get_recommendation(
        db, recommendation_id, current_user.org_id,
    )
    changes: dict[str, object] = {}
    if payload.status is not None:
        changes["status"] = payload.status
    if payload.reason is not None:
        changes["reason"] = payload.reason
    if changes:
        await db.execute(
            update(ActionRecommendation)
            .where(
                ActionRecommendation.id == recommendation_id,
            )
            .values(**changes)
        )
        await db.commit()
        await db.refresh(rec)
    return ActionRecommendationOut.model_validate(rec)


@router.get(
    "/api/deals/{deal_id}/drafts",
    response_model=list[FollowupDraftOut],
)
async def list_drafts(
    deal_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[FollowupDraftOut]:
    """List follow-up drafts for a deal."""
    await _verify_deal_access(db, deal_id, current_user.org_id)
    result = await db.execute(
        select(FollowupDraft)
        .where(FollowupDraft.deal_id == deal_id)
        .order_by(FollowupDraft.created_at.desc())
    )
    return [
        FollowupDraftOut.model_validate(d)
        for d in result.scalars().all()
    ]


@router.get(
    "/api/deals/{deal_id}/risk",
    response_model=RiskSnapshotOut | None,
)
async def get_latest_risk(
    deal_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> RiskSnapshotOut | None:
    """Return the latest risk snapshot for a deal."""
    await _verify_deal_access(db, deal_id, current_user.org_id)
    result = await db.execute(
        select(RiskSnapshot)
        .where(RiskSnapshot.deal_id == deal_id)
        .order_by(RiskSnapshot.created_at.desc())
        .limit(1)
    )
    snap = result.scalar_one_or_none()
    if snap is None:
        return None
    return RiskSnapshotOut.model_validate(snap)


async def _get_recommendation(
    db: AsyncSession,
    recommendation_id: uuid.UUID,
    org_id: uuid.UUID,
) -> ActionRecommendation:
    """Load a recommendation with org-scoped access check."""
    row = await db.execute(
        select(ActionRecommendation)
        .join(Deal, Deal.id == ActionRecommendation.deal_id)
        .where(
            ActionRecommendation.id == recommendation_id,
            Deal.org_id == org_id,
        )
    )
    rec = row.scalar_one_or_none()
    if rec is None:
        raise NotFoundError("Recommendation not found.")
    return rec
