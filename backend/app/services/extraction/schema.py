"""Pydantic extraction schema for structured Gemini output.

Matches the PRD minimum extraction schema (section 18.1).
Version changes to this schema must bump ``SCHEMA_VERSION``.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

SCHEMA_VERSION = "1.0"
PROMPT_VERSION = "1.0"


class StakeholderExtraction(BaseModel):
    name: str = Field(description="Stakeholder name.")
    title: str = Field(description="Stakeholder title.")
    role_label: str = Field(
        description=(
            "Role in buying process: champion, blocker, "
            "economic_buyer, influencer, procurement, "
            "legal, or unknown."
        ),
    )
    role_confidence: float = Field(
        description="Confidence in role label, 0.0 to 1.0.",
    )


class QualificationExtraction(BaseModel):
    budget_signal: str = Field(
        description="Budget signal: positive, negative, or unknown.",
    )
    authority_signal: str = Field(
        description=(
            "Authority signal: positive, negative, or unknown."
        ),
    )
    need_signal: str = Field(
        description="Need signal: positive, negative, or unknown.",
    )
    timeline_signal: str = Field(
        description=(
            "Timeline signal: positive, negative, or unknown."
        ),
    )


class DealSignalsExtraction(BaseModel):
    pain_points: list[str] = Field(
        default_factory=list,
        description="Pain points mentioned.",
    )
    objections: list[str] = Field(
        default_factory=list,
        description="Objections raised.",
    )
    competitors: list[str] = Field(
        default_factory=list,
        description="Competitor mentions.",
    )
    security_mentions: list[str] = Field(
        default_factory=list,
        description="Security or compliance mentions.",
    )
    procurement_mentions: list[str] = Field(
        default_factory=list,
        description="Procurement process mentions.",
    )
    next_step: str = Field(
        default="",
        description="Agreed or suggested next step.",
    )
    timeline_detail: str = Field(
        default="",
        description="Timeline detail or deadline mentioned.",
    )
    budget_detail: str = Field(
        default="",
        description="Budget detail or amount mentioned.",
    )


class InteractionExtraction(BaseModel):
    sentiment: str = Field(
        description="Overall sentiment: positive, neutral, or negative.",
    )
    engagement_level: str = Field(
        description="Engagement level: high, medium, or low.",
    )
    followup_requested: bool = Field(
        description="Whether a follow-up was requested.",
    )


class EvidenceItem(BaseModel):
    field: str = Field(
        description=(
            "Extraction field this evidence supports, "
            "e.g. 'next_step' or 'budget_signal'."
        ),
    )
    quote: str = Field(
        description="Verbatim quote from the transcript.",
    )
    speaker: str = Field(
        description="Speaker: agent or prospect.",
    )
    sequence_number: int = Field(
        description=(
            "Utterance sequence number in the transcript."
        ),
    )


class CallExtraction(BaseModel):
    """Top-level extraction artifact from a call transcript."""

    stakeholder: StakeholderExtraction
    qualification: QualificationExtraction
    deal_signals: DealSignalsExtraction
    interaction: InteractionExtraction
    evidence: list[EvidenceItem] = Field(
        default_factory=list,
        description=(
            "Evidence anchors linking extracted fields "
            "to transcript quotes."
        ),
    )
    summary: str = Field(
        description="Concise 2-3 sentence call summary.",
    )
    confidence: float = Field(
        description="Overall extraction confidence, 0.0 to 1.0.",
    )
