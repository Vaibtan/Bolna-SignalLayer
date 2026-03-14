"""TranscriptUtterance model."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import text as sa_text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TranscriptUtterance(Base):
    __tablename__ = "transcript_utterances"
    __table_args__ = (
        Index(
            "ix_transcript_utterances_call_session_id",
            "call_session_id",
        ),
        UniqueConstraint(
            "call_session_id",
            "sequence_number",
            name="uq_transcript_utterances_call_session_sequence",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=sa_text("gen_random_uuid()"),
    )
    call_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("call_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider_segment_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
    )
    speaker: Mapped[str] = mapped_column(String(64), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    start_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    is_final: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=sa_text("true"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sa_text("now()"),
    )
