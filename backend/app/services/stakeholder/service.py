"""Stakeholder CRUD service."""

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.deal import Deal
from app.models.stakeholder import Stakeholder
from app.schemas.stakeholder import StakeholderCreate, StakeholderUpdate


async def create_stakeholder(
    db: AsyncSession,
    org_id: uuid.UUID,
    deal_id: uuid.UUID,
    payload: StakeholderCreate,
) -> Stakeholder:
    """Insert a stakeholder under a deal."""
    result = await db.execute(
        select(Deal.id).where(Deal.id == deal_id, Deal.org_id == org_id)
    )
    if result.scalar_one_or_none() is None:
        raise NotFoundError("Deal not found.")

    stakeholder = Stakeholder(
        deal_id=deal_id,
        name=payload.name,
        title=payload.title,
        department=payload.department,
        email=payload.email,
        phone=payload.phone,
        source_type=payload.source_type,
        metadata_json=payload.metadata_json,
    )
    db.add(stakeholder)
    await db.flush()
    return stakeholder


async def list_stakeholders(
    db: AsyncSession,
    org_id: uuid.UUID,
    deal_id: uuid.UUID,
) -> list[Stakeholder]:
    """Return all stakeholders for a deal (org-scoped via JOIN)."""
    result = await db.execute(
        select(Stakeholder)
        .join(Deal, Deal.id == Stakeholder.deal_id)
        .where(Stakeholder.deal_id == deal_id, Deal.org_id == org_id)
        .order_by(Stakeholder.created_at.desc())
    )
    return list(result.scalars().all())


async def get_stakeholder(
    db: AsyncSession,
    org_id: uuid.UUID,
    deal_id: uuid.UUID,
    stakeholder_id: uuid.UUID,
) -> Stakeholder:
    """Fetch a single stakeholder by ID (org-scoped via JOIN)."""
    result = await db.execute(
        select(Stakeholder)
        .join(Deal, Deal.id == Stakeholder.deal_id)
        .where(
            Stakeholder.id == stakeholder_id,
            Stakeholder.deal_id == deal_id,
            Deal.org_id == org_id,
        )
    )
    stakeholder = result.scalar_one_or_none()
    if stakeholder is None:
        raise NotFoundError("Stakeholder not found.")
    return stakeholder


async def update_stakeholder(
    db: AsyncSession,
    org_id: uuid.UUID,
    deal_id: uuid.UUID,
    stakeholder_id: uuid.UUID,
    payload: StakeholderUpdate,
) -> Stakeholder:
    """Patch a stakeholder and return the updated row."""
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return await get_stakeholder(db, org_id, deal_id, stakeholder_id)

    # Verify org access before updating
    result = await db.execute(
        select(Deal.id).where(Deal.id == deal_id, Deal.org_id == org_id)
    )
    if result.scalar_one_or_none() is None:
        raise NotFoundError("Deal not found.")

    changes['updated_at'] = func.now()
    result = await db.execute(
        update(Stakeholder)
        .where(
            Stakeholder.id == stakeholder_id,
            Stakeholder.deal_id == deal_id,
        )
        .values(**changes)
        .returning(Stakeholder.id)
    )
    updated_id = result.scalar_one_or_none()
    if updated_id is None:
        raise NotFoundError("Stakeholder not found.")
    return await get_stakeholder(db, org_id, deal_id, stakeholder_id)
