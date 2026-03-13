"""Call initiation request and response schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CallInitiateRequest(BaseModel):
    stakeholder_id: uuid.UUID
    objective: str = Field(
        pattern=r"^(discovery_qualification|timeline_procurement_validation|blocker_clarification)$",
    )
    topics: str | None = Field(default=None, max_length=500)


class CallSessionOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    deal_id: uuid.UUID
    stakeholder_id: uuid.UUID
    provider_name: str
    provider_call_id: str | None
    status: str
    processing_status: str
    objective: str | None
    initiated_by_user_id: uuid.UUID | None
    started_at: datetime | None
    ended_at: datetime | None
    duration_seconds: int | None
    recording_url: str | None
    provider_metadata_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime
