"""Schemas for intelligence endpoints (recommendations, drafts, risk)."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ActionRecommendationOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    deal_id: uuid.UUID
    call_session_id: uuid.UUID | None
    target_stakeholder_id: uuid.UUID | None
    action_type: str
    reason: str
    confidence: float | None
    status: str
    payload_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class FollowupDraftOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    deal_id: uuid.UUID
    call_session_id: uuid.UUID
    draft_type: str
    subject: str | None
    body_text: str
    tone: str
    status: str
    created_at: datetime
    updated_at: datetime


class RiskSnapshotOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    deal_id: uuid.UUID
    call_session_id: uuid.UUID | None
    score: int
    level: str
    factors_json: dict[str, Any] | None
    change_summary_json: dict[str, Any] | None
    created_at: datetime


class RecommendationStatusUpdate(BaseModel):
    status: str | None = None
    reason: str | None = None
