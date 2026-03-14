"""StakeholderSnapshot model — append-only."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StakeholderSnapshot(Base):
    __tablename__ = "stakeholder_snapshots"
    __table_args__ = (
        Index(
            "ix_stakeholder_snapshots_stakeholder_id",
            "stakeholder_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    stakeholder_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stakeholders.id", ondelete="CASCADE"),
        nullable=False,
    )
    summary: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    role_label: Mapped[str | None] = mapped_column(
        String(64), nullable=True,
    )
    role_confidence: Mapped[float | None] = mapped_column(
        Float, nullable=True,
    )
    stance: Mapped[str | None] = mapped_column(
        String(64), nullable=True,
    )
    sentiment: Mapped[str | None] = mapped_column(
        String(64), nullable=True,
    )
    open_questions_json: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
    )
