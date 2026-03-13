"""Deal request and response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DealCreate(BaseModel):
    name: str = Field(max_length=255)
    account_name: str = Field(max_length=255)
    stage: str = Field(default="discovery", max_length=64)
    owner_user_id: uuid.UUID | None = None


class DealUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    account_name: str | None = Field(default=None, max_length=255)
    stage: str | None = Field(default=None, max_length=64)
    owner_user_id: uuid.UUID | None = None


class DealOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    account_name: str
    stage: str
    owner_user_id: uuid.UUID | None
    risk_score_current: int | None
    risk_level_current: str | None
    coverage_status_current: str | None
    summary_current: str | None
    created_at: datetime
    updated_at: datetime
