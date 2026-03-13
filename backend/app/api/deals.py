"""Deal API endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.deal import DealCreate, DealOut, DealUpdate
from app.services.deal import service as deal_svc

router = APIRouter(prefix="/api/deals", tags=["deals"])


@router.post("", response_model=DealOut, status_code=201)
async def create_deal(
    payload: DealCreate,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DealOut:
    """Create a new deal in the current user's organization."""
    deal = await deal_svc.create_deal(db, current_user.org_id, payload)
    await db.commit()
    return DealOut.model_validate(deal)


@router.get("", response_model=list[DealOut])
async def list_deals(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[DealOut]:
    """List all deals for the current organization."""
    deals = await deal_svc.list_deals(db, current_user.org_id)
    return [DealOut.model_validate(d) for d in deals]


@router.get("/{deal_id}", response_model=DealOut)
async def get_deal(
    deal_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DealOut:
    """Fetch a single deal by ID."""
    deal = await deal_svc.get_deal(db, current_user.org_id, deal_id)
    return DealOut.model_validate(deal)


@router.patch("/{deal_id}", response_model=DealOut)
async def update_deal(
    deal_id: uuid.UUID,
    payload: DealUpdate,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DealOut:
    """Update a deal."""
    deal = await deal_svc.update_deal(
        db, current_user.org_id, deal_id, payload
    )
    await db.commit()
    return DealOut.model_validate(deal)
