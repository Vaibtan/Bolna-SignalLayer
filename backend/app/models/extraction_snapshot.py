"""ExtractionSnapshot model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ExtractionSnapshot(Base):
    """Append-only structured extraction artifact for a completed call."""

    __tablename__ = "extraction_snapshots"
    __table_args__ = (
        Index(
            "ix_extraction_snapshots_call_session_id",
            "call_session_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    call_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("call_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    extracted_json: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
    )
