"""ActionRecommendation model."""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

_STATUSES = ("proposed", "accepted", "dismissed", "edited", "expired")


class ActionRecommendation(Base):
    __tablename__ = "action_recommendations"
    __table_args__ = (
        Index("ix_action_recommendations_deal_id", "deal_id"),
        CheckConstraint(
            f"status IN ({', '.join(repr(s) for s in _STATUSES)})",
            name="ck_action_recommendations_status",
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
    call_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("call_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_stakeholder_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("stakeholders.id", ondelete="SET NULL"),
        nullable=True,
    )
    action_type: Mapped[str] = mapped_column(
        String(64), nullable=False,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(
        Float, nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'proposed'"),
    )
    payload_json: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
    )
