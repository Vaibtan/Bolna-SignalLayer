"""Stakeholder model."""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Stakeholder(Base):
    __tablename__ = "stakeholders"
    __table_args__ = (
        Index("ix_stakeholders_deal_id", "deal_id"),
        CheckConstraint(
            "source_type IN ('manual', 'inferred')",
            name="ck_stakeholders_source_type",
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
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    role_label_current: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    role_confidence_current: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    stance_current: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    sentiment_current: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    last_contacted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source_type: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=text("'manual'")
    )
    metadata_json: Mapped[dict[str, object] | None] = mapped_column(
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
