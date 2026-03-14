"""RiskSnapshot model — append-only."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RiskSnapshot(Base):
    __tablename__ = "risk_snapshots"
    __table_args__ = (
        Index("ix_risk_snapshots_deal_id", "deal_id"),
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
    score: Mapped[int] = mapped_column(
        Integer, nullable=False,
    )
    level: Mapped[str] = mapped_column(
        String(32), nullable=False,
    )
    factors_json: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True,
    )
    change_summary_json: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True,
    )
    model_metadata_json: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
    )
