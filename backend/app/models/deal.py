"""Deal model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Deal(Base):
    __tablename__ = "deals"
    __table_args__ = (
        Index("ix_deals_org_id", "org_id"),
        Index("ix_deals_owner_user_id", "owner_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stage: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default=text("'discovery'")
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    risk_score_current: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    risk_level_current: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    coverage_status_current: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    summary_current: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
    )
