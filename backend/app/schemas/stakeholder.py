"""Stakeholder request and response schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class StakeholderCreate(BaseModel):
    name: str = Field(max_length=255)
    title: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=64)
    source_type: str = Field(default="manual", pattern=r"^(manual|inferred)$")
    metadata_json: dict[str, Any] | None = None


class StakeholderUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    title: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=64)
    metadata_json: dict[str, Any] | None = None


class StakeholderOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    deal_id: uuid.UUID
    name: str
    title: str | None
    department: str | None
    email: str | None
    phone: str | None
    role_label_current: str | None
    role_confidence_current: float | None
    stance_current: str | None
    sentiment_current: str | None
    last_contacted_at: datetime | None
    source_type: str
    metadata_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime
