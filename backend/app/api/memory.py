"""Memory search API endpoints."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import NotFoundError
from app.db.session import get_db_session
from app.models.deal import Deal
from app.models.stakeholder import Stakeholder
from app.models.user import User
from app.services.memory.service import (
    search_memory,
    search_stakeholder_memory,
)

router = APIRouter(tags=["memory"])


@router.get("/api/deals/{deal_id}/memory/search")
async def deal_memory_search(
    deal_id: uuid.UUID,
    q: Annotated[str, Query(min_length=1, max_length=500)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    doc_type: str | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Semantic search over deal memory documents."""
    await _verify_deal(db, deal_id, current_user.org_id)
    return await search_memory(
        db,
        deal_id,
        q,
        doc_type=doc_type,
        limit=min(limit, 20),
    )


@router.get("/api/deals/{deal_id}/memory/similar-calls")
async def similar_calls(
    deal_id: uuid.UUID,
    q: Annotated[str, Query(min_length=1, max_length=500)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Find similar calls within a deal."""
    await _verify_deal(db, deal_id, current_user.org_id)
    return await search_memory(
        db,
        deal_id,
        q,
        doc_type="call_summary",
        limit=min(limit, 20),
    )


@router.get("/api/stakeholders/{stakeholder_id}/memory")
async def stakeholder_memory(
    stakeholder_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Return memory documents for a stakeholder."""
    await _verify_stakeholder(
        db, stakeholder_id, current_user.org_id,
    )
    docs = await search_stakeholder_memory(
        db, stakeholder_id, limit=min(limit, 50),
    )
    return [
        {
            "id": str(d.id),
            "doc_type": d.doc_type,
            "content": d.content,
            "call_session_id": (
                str(d.call_session_id)
                if d.call_session_id
                else None
            ),
            "created_at": d.created_at.isoformat(),
        }
        for d in docs
    ]


async def _verify_deal(
    db: AsyncSession,
    deal_id: uuid.UUID,
    org_id: uuid.UUID,
) -> None:
    row = await db.execute(
        select(Deal).where(
            Deal.id == deal_id,
            Deal.org_id == org_id,
        )
    )
    if row.scalar_one_or_none() is None:
        raise NotFoundError("Deal not found.")


async def _verify_stakeholder(
    db: AsyncSession,
    stakeholder_id: uuid.UUID,
    org_id: uuid.UUID,
) -> None:
    row = await db.execute(
        select(Stakeholder)
        .join(Deal, Deal.id == Stakeholder.deal_id)
        .where(
            Stakeholder.id == stakeholder_id,
            Deal.org_id == org_id,
        )
    )
    if row.scalar_one_or_none() is None:
        raise NotFoundError("Stakeholder not found.")
