"""Memory document generation and semantic search.

Generates vectorized memory documents from post-call
artifacts and provides similarity search over pgvector.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import structlog
from google import genai
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.call_session import CallSession
from app.models.deal import Deal
from app.models.extraction_snapshot import ExtractionSnapshot
from app.models.memory_document import MemoryDocument
from app.models.risk_snapshot import RiskSnapshot
from app.models.stakeholder import Stakeholder

logger = structlog.get_logger(__name__)

DOC_TYPES = (
    "call_summary",
    "objection_summary",
    "stakeholder_profile_summary",
    "deal_state_summary",
    "action_rationale_summary",
)


def _build_documents(
    deal: Deal,
    extraction: ExtractionSnapshot,
    risk: RiskSnapshot | None,
    stakeholder: Stakeholder | None,
    call_session_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """Build memory document contents from post-call artifacts."""
    extracted: dict[str, Any] = dict(extraction.extracted_json)
    docs: list[dict[str, Any]] = []

    # 1. Call summary.
    summary = extraction.summary or ""
    if summary:
        docs.append({
            "doc_type": "call_summary",
            "content": summary,
            "stakeholder_id": (
                stakeholder.id if stakeholder else None
            ),
        })

    # 2. Objection summary.
    objections = (
        extracted.get("deal_signals", {}).get("objections", [])
    )
    if objections:
        obj_text = (
            f"Objections raised during call: "
            f"{'; '.join(str(o) for o in objections)}"
        )
        docs.append({
            "doc_type": "objection_summary",
            "content": obj_text,
        })

    # 3. Stakeholder profile summary.
    sh_data = extracted.get("stakeholder", {})
    if stakeholder and sh_data:
        sentiment = extracted.get(
            "interaction", {},
        ).get("sentiment", "unknown")
        profile = (
            f"{sh_data.get('name', stakeholder.name)}, "
            f"{sh_data.get('title', '')}. "
            f"Role: {sh_data.get('role_label', 'unknown')}. "
            f"Sentiment: {sentiment}."
        )
        docs.append({
            "doc_type": "stakeholder_profile_summary",
            "content": profile,
            "stakeholder_id": stakeholder.id,
        })

    # 4. Deal state summary.
    signals = extracted.get("deal_signals", {})
    deal_text = (
        f"Deal: {deal.name} ({deal.account_name}). "
        f"Stage: {deal.stage or 'unknown'}. "
        f"Next step: {signals.get('next_step', 'none')}. "
        f"Risk: {risk.level if risk else 'unknown'} "
        f"({risk.score if risk else '?'}/100)."
    )
    docs.append({
        "doc_type": "deal_state_summary",
        "content": deal_text,
    })

    # 5. Action rationale summary.
    if risk:
        raw_factors = (risk.factors_json or {}).get(
            "factors", [],
        )
        factors: list[str] = (
            list(raw_factors)
            if isinstance(raw_factors, list)
            else []
        )
        if factors:
            rationale = (
                f"Risk factors: {'; '.join(factors)}. "
                f"Score: {risk.score}/100 ({risk.level})."
            )
            docs.append({
                "doc_type": "action_rationale_summary",
                "content": rationale,
            })

    # Add common fields.
    for doc in docs:
        doc.setdefault("stakeholder_id", None)
        doc["deal_id"] = deal.id
        doc["call_session_id"] = call_session_id

    return docs


def _embed_text_sync(
    client: genai.Client,
    model: str,
    content: str,
) -> list[float] | None:
    """Synchronous embedding call (for thread pool)."""
    try:
        result = client.models.embed_content(
            model=model,
            contents=content,
        )
        if result and result.embeddings:
            values = result.embeddings[0].values
            if values is not None:
                return list(values)
    except Exception:
        logger.warning(
            "memory.embedding_failed",
            exc_info=True,
        )
    return None


async def _embed_text(
    client: genai.Client,
    model: str,
    content: str,
) -> list[float] | None:
    """Generate an embedding vector without blocking the loop."""
    return await asyncio.to_thread(
        _embed_text_sync, client, model, content,
    )


async def generate_memory_documents(
    db: AsyncSession,
    call_session_id: uuid.UUID,
) -> list[MemoryDocument]:
    """Generate and embed memory documents for a call.

    This is a non-blocking operation — failures here
    do not affect the main processing pipeline.
    """
    settings = get_settings()

    # 0. Idempotency: skip if documents already exist.
    existing = await db.execute(
        select(MemoryDocument.id)
        .where(
            MemoryDocument.call_session_id
            == call_session_id,
        )
        .limit(1)
    )
    if existing.scalar_one_or_none() is not None:
        logger.debug(
            "memory.already_generated",
            call_session_id=str(call_session_id),
        )
        return []

    # 1. Load context.
    cs_row = await db.execute(
        select(CallSession).where(
            CallSession.id == call_session_id,
        )
    )
    session = cs_row.scalar_one_or_none()
    if session is None:
        return []

    deal_row = await db.execute(
        select(Deal).where(Deal.id == session.deal_id)
    )
    deal = deal_row.scalar_one_or_none()
    if deal is None:
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
    if extraction is None:
        return []

    risk_row = await db.execute(
        select(RiskSnapshot)
        .where(RiskSnapshot.deal_id == deal.id)
        .order_by(RiskSnapshot.created_at.desc())
        .limit(1)
    )
    risk = risk_row.scalar_one_or_none()

    sh_row = await db.execute(
        select(Stakeholder).where(
            Stakeholder.id == session.stakeholder_id,
        )
    )
    stakeholder = sh_row.scalar_one_or_none()

    # 2. Build documents.
    doc_defs = _build_documents(
        deal, extraction, risk, stakeholder, call_session_id,
    )

    # 3. Embed and persist.
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    model = settings.GEMINI_MODEL_EMBEDDING
    persisted: list[MemoryDocument] = []

    for doc_def in doc_defs:
        embedding = await _embed_text(
            client, model, doc_def["content"],
        )
        mem = MemoryDocument(
            deal_id=doc_def["deal_id"],
            stakeholder_id=doc_def.get("stakeholder_id"),
            call_session_id=doc_def.get("call_session_id"),
            doc_type=doc_def["doc_type"],
            content=doc_def["content"],
            metadata_json={
                "model": model,
                "call_session_id": str(call_session_id),
            },
            embedding=embedding,
        )
        db.add(mem)
        persisted.append(mem)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        logger.info(
            "memory.duplicate_generation_skipped",
            call_session_id=str(call_session_id),
        )
        return []

    logger.info(
        "memory.documents_generated",
        call_session_id=str(call_session_id),
        count=len(persisted),
        embedded=sum(
            1 for m in persisted if m.embedding is not None
        ),
    )
    return persisted


async def search_memory(
    db: AsyncSession,
    deal_id: uuid.UUID,
    query_text: str,
    *,
    doc_type: str | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Search memory documents by cosine similarity.

    Returns documents with similarity scores, ordered
    by relevance.
    """
    settings = get_settings()
    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    query_embedding = await _embed_text(
        client,
        settings.GEMINI_MODEL_EMBEDDING,
        query_text,
    )
    if query_embedding is None:
        return []

    # Build the query with cosine distance.
    stmt = (
        select(
            MemoryDocument,
            MemoryDocument.embedding.cosine_distance(
                query_embedding,
            ).label("distance"),
        )
        .where(
            MemoryDocument.deal_id == deal_id,
            MemoryDocument.embedding.is_not(None),
        )
        .order_by(text("distance"))
        .limit(limit)
    )

    if doc_type:
        stmt = stmt.where(MemoryDocument.doc_type == doc_type)

    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "id": str(doc.id),
            "doc_type": doc.doc_type,
            "content": doc.content,
            "stakeholder_id": (
                str(doc.stakeholder_id)
                if doc.stakeholder_id
                else None
            ),
            "call_session_id": (
                str(doc.call_session_id)
                if doc.call_session_id
                else None
            ),
            "similarity": round(1 - distance, 4),
            "created_at": doc.created_at.isoformat(),
        }
        for doc, distance in rows
    ]


async def search_stakeholder_memory(
    db: AsyncSession,
    stakeholder_id: uuid.UUID,
    *,
    limit: int = 10,
) -> list[MemoryDocument]:
    """Return memory documents for a stakeholder."""
    result = await db.execute(
        select(MemoryDocument)
        .where(
            MemoryDocument.stakeholder_id == stakeholder_id,
        )
        .order_by(MemoryDocument.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
