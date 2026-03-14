"""Pydantic schema for Gemini recommendation output."""

from __future__ import annotations

from pydantic import BaseModel, Field

SCHEMA_VERSION = "1.0"
PROMPT_VERSION = "1.0"


class RecommendationItem(BaseModel):
    action_type: str = Field(
        description=(
            "Action type: call_stakeholder, send_followup, "
            "request_intro, send_collateral, confirm_timeline, "
            "escalate, book_meeting, or deprioritize."
        ),
    )
    target_stakeholder_name: str = Field(
        default="",
        description="Name of the target stakeholder, if any.",
    )
    reason: str = Field(
        description="Why this action matters now.",
    )
    confidence: float = Field(
        description="Confidence in this recommendation, 0-1.",
    )
    talk_track: str = Field(
        default="",
        description="Suggested talk track or approach.",
    )


class FollowupDraftItem(BaseModel):
    draft_type: str = Field(
        description=(
            "Draft type: email, crm_note, or followup."
        ),
    )
    subject: str = Field(
        default="",
        description="Email subject line, if applicable.",
    )
    body_text: str = Field(
        description="Full draft text.",
    )
    tone: str = Field(
        default="professional",
        description="Tone: professional, friendly, or urgent.",
    )


class RecommendationOutput(BaseModel):
    """Top-level recommendation artifact from Gemini."""

    recommendations: list[RecommendationItem] = Field(
        description="1-3 next best actions.",
    )
    drafts: list[FollowupDraftItem] = Field(
        description=(
            "Follow-up drafts. Must include at least one "
            "crm_note entry."
        ),
    )
