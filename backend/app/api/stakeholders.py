"""Stakeholder API endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.stakeholder import (
    StakeholderCreate,
    StakeholderOut,
    StakeholderUpdate,
)
from app.services.stakeholder import service as stakeholder_svc

router = APIRouter(
    prefix="/api/deals/{deal_id}/stakeholders", tags=["stakeholders"]
)


@router.post("", response_model=StakeholderOut, status_code=201)
async def create_stakeholder(
    deal_id: uuid.UUID,
    payload: StakeholderCreate,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> StakeholderOut:
    """Create a stakeholder under a deal."""
    sh = await stakeholder_svc.create_stakeholder(
        db, current_user.org_id, deal_id, payload
    )
    await db.commit()
    return StakeholderOut.model_validate(sh)


@router.get("", response_model=list[StakeholderOut])
async def list_stakeholders(
    deal_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[StakeholderOut]:
    """List all stakeholders for a deal."""
    shs = await stakeholder_svc.list_stakeholders(
        db, current_user.org_id, deal_id
    )
    return [StakeholderOut.model_validate(s) for s in shs]


@router.get("/{stakeholder_id}", response_model=StakeholderOut)
async def get_stakeholder(
    deal_id: uuid.UUID,
    stakeholder_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> StakeholderOut:
    """Fetch a single stakeholder."""
    sh = await stakeholder_svc.get_stakeholder(
        db, current_user.org_id, deal_id, stakeholder_id
    )
    return StakeholderOut.model_validate(sh)


@router.patch("/{stakeholder_id}", response_model=StakeholderOut)
async def update_stakeholder(
    deal_id: uuid.UUID,
    stakeholder_id: uuid.UUID,
    payload: StakeholderUpdate,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> StakeholderOut:
    """Update a stakeholder."""
    sh = await stakeholder_svc.update_stakeholder(
        db, current_user.org_id, deal_id, stakeholder_id, payload
    )
    await db.commit()
    return StakeholderOut.model_validate(sh)
