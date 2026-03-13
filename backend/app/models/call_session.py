"""CallSession model."""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

_CALL_STATES = (
    "initiating",
    "queued",
    "ringing",
    "in_progress",
    "completed",
    "no_answer",
    "busy",
    "failed",
    "canceled",
)

_PROCESSING_STATES = (
    "pending",
    "transcript_partial",
    "transcript_finalized",
    "extraction_running",
    "extraction_completed",
    "snapshots_updating",
    "risk_running",
    "recommendation_completed",
    "failed_retryable",
    "failed_terminal",
)


class CallSession(Base):
    __tablename__ = "call_sessions"
    __table_args__ = (
        Index("ix_call_sessions_deal_id", "deal_id"),
        Index("ix_call_sessions_stakeholder_id", "stakeholder_id"),
        Index(
            "ix_call_sessions_provider_call_id",
            "provider_call_id",
        ),
        CheckConstraint(
            f"status IN ({', '.join(repr(s) for s in _CALL_STATES)})",
            name="ck_call_sessions_status",
        ),
        CheckConstraint(
            'processing_status IN '
            f"({', '.join(repr(s) for s in _PROCESSING_STATES)})",
            name="ck_call_sessions_processing_status",
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
    stakeholder_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stakeholders.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider_name: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_call_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=text("'initiating'")
    )
    processing_status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=text("'pending'")
    )
    objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    initiated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_seconds: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    recording_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_metadata_json: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
    )
