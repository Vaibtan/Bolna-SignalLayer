"""Deal CRUD service."""

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.deal import Deal
from app.models.user import User
from app.schemas.deal import DealCreate, DealUpdate


async def _validate_owner_user(
    db: AsyncSession,
    org_id: uuid.UUID,
    owner_user_id: uuid.UUID | None,
) -> None:
    """Ensure the requested owner belongs to the current organization."""
    if owner_user_id is None:
        return

    result = await db.execute(
        select(User.id).where(
            User.id == owner_user_id,
            User.org_id == org_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise NotFoundError('Owner user not found.')


async def create_deal(
    db: AsyncSession,
    org_id: uuid.UUID,
    payload: DealCreate,
) -> Deal:
    """Insert a new deal and return it."""
    await _validate_owner_user(db, org_id, payload.owner_user_id)

    deal = Deal(
        org_id=org_id,
        name=payload.name,
        account_name=payload.account_name,
        stage=payload.stage,
        owner_user_id=payload.owner_user_id,
    )
    db.add(deal)
    await db.flush()
    return deal


async def list_deals(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> list[Deal]:
    """Return all deals for an organization."""
    result = await db.execute(
        select(Deal)
        .where(Deal.org_id == org_id)
        .order_by(Deal.created_at.desc())
    )
    return list(result.scalars().all())


async def get_deal(
    db: AsyncSession,
    org_id: uuid.UUID,
    deal_id: uuid.UUID,
) -> Deal:
    """Fetch a single deal by ID, scoped to org."""
    result = await db.execute(
        select(Deal).where(Deal.id == deal_id, Deal.org_id == org_id)
    )
    deal = result.scalar_one_or_none()
    if deal is None:
        raise NotFoundError("Deal not found.")
    return deal


async def update_deal(
    db: AsyncSession,
    org_id: uuid.UUID,
    deal_id: uuid.UUID,
    payload: DealUpdate,
) -> Deal:
    """Patch a deal and return the updated row."""
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return await get_deal(db, org_id, deal_id)

    await _validate_owner_user(
        db,
        org_id,
        changes.get('owner_user_id'),
    )

    changes['updated_at'] = func.now()
    result = await db.execute(
        update(Deal)
        .where(Deal.id == deal_id, Deal.org_id == org_id)
        .values(**changes)
        .returning(Deal)
    )
    deal = result.scalar_one_or_none()
    if deal is None:
        raise NotFoundError("Deal not found.")
    return deal
