"""EvidenceAnchor model."""

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EvidenceAnchor(Base):
    """Links an extracted field to a transcript quote."""

    __tablename__ = "evidence_anchors"
    __table_args__ = (
        Index(
            "ix_evidence_anchors_call_session_id",
            "call_session_id",
        ),
        Index(
            "ix_evidence_anchors_artifact",
            "artifact_type",
            "artifact_id",
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
    artifact_type: Mapped[str] = mapped_column(
        String(64), nullable=False,
    )
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        nullable=False,
    )
    field_name: Mapped[str] = mapped_column(
        String(128), nullable=False,
    )
    transcript_utterance_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "transcript_utterances.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    quote_text: Mapped[str] = mapped_column(Text, nullable=False)
    speaker: Mapped[str] = mapped_column(
        String(64), nullable=False,
    )
    sequence_number: Mapped[int] = mapped_column(
        Integer, nullable=False,
    )
    confidence: Mapped[float | None] = mapped_column(
        Float, nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
    )
