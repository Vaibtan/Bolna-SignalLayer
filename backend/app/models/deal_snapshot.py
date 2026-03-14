"""DealSnapshot model — append-only."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DealSnapshot(Base):
    __tablename__ = "deal_snapshots"
    __table_args__ = (
        Index("ix_deal_snapshots_deal_id", "deal_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    deal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
    )
    summary: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    coverage_status: Mapped[str | None] = mapped_column(
        String(64), nullable=True,
    )
    open_questions_json: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True,
    )
    key_signals_json: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
    )
