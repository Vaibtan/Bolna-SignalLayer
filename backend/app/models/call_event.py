"""CallEvent model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CallEvent(Base):
    __tablename__ = "call_events"
    __table_args__ = (
        Index("ix_call_events_call_session_id", "call_session_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    call_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("call_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider_event_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    sequence_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload_json: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
    )
