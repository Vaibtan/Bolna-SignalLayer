"""FollowupDraft model."""

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FollowupDraft(Base):
    __tablename__ = "followup_drafts"
    __table_args__ = (
        Index("ix_followup_drafts_deal_id", "deal_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    deal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
    )
    call_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("call_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    draft_type: Mapped[str] = mapped_column(
        String(64), nullable=False,
    )
    subject: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    tone: Mapped[str] = mapped_column(
        String(32), nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'draft'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
    )
