"""MemoryDocument model — vectorized memory for semantic retrieval."""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

EMBEDDING_DIMENSIONS = 3072


class MemoryDocument(Base):
    __tablename__ = "memory_documents"
    __table_args__ = (
        Index("ix_memory_documents_deal_id", "deal_id"),
        Index(
            "ix_memory_documents_stakeholder_id",
            "stakeholder_id",
        ),
        Index(
            "ix_memory_documents_doc_type",
            "doc_type",
        ),
        UniqueConstraint(
            "call_session_id",
            "doc_type",
            name="uq_memory_documents_call_session_doc_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    deal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
    )
    stakeholder_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("stakeholders.id", ondelete="SET NULL"),
        nullable=True,
    )
    call_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("call_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    doc_type: Mapped[str] = mapped_column(
        String(64), nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True,
    )
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMBEDDING_DIMENSIONS), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
    )
