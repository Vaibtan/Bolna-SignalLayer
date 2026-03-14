"""Deterministic risk scoring rules.

Each rule inspects the extraction payload and returns
(points, factor_description) when the condition is met.
The total score is capped at 100.
"""

from __future__ import annotations

from typing import Any


def _get(data: dict[str, Any], *keys: str) -> Any:
    """Nested dict lookup."""
    val: Any = data
    for k in keys:
        if not isinstance(val, dict):
            return None
        val = val.get(k)
    return val


def score_extraction(
    extracted: dict[str, Any],
    stakeholder_count: int,
) -> tuple[int, list[str]]:
    """Run all deterministic risk rules.

    Returns ``(score, factors)`` where *score* is 0-100
    and *factors* is a list of human-readable strings
    describing active risk factors.
    """
    points = 0
    factors: list[str] = []

    def _add(pts: int, factor: str) -> None:
        nonlocal points
        points += pts
        factors.append(factor)

    # 1. No committed next step.
    next_step = _get(extracted, "deal_signals", "next_step")
    if not next_step or not str(next_step).strip():
        _add(15, "No committed next step")

    # 2. No economic buyer identified.
    role = _get(extracted, "stakeholder", "role_label")
    if role != "economic_buyer":
        _add(15, "No economic buyer identified")

    # 3. Single-threaded account.
    if stakeholder_count <= 1:
        _add(10, "Single-threaded account")

    # 4. Negative sentiment.
    sentiment = _get(extracted, "interaction", "sentiment")
    if sentiment == "negative":
        _add(12, "Negative sentiment detected")

    # 5. Low engagement.
    engagement = _get(
        extracted, "interaction", "engagement_level",
    )
    if engagement == "low":
        _add(8, "Low engagement level")

    # 6. Security / compliance blocker.
    sec = _get(extracted, "deal_signals", "security_mentions")
    if isinstance(sec, list) and sec:
        _add(10, "Security or compliance blocker raised")

    # 7. Procurement blocker.
    proc = _get(
        extracted, "deal_signals", "procurement_mentions",
    )
    if isinstance(proc, list) and proc:
        _add(8, "Procurement process blocker")

    # 8. Budget uncertainty.
    budget = _get(extracted, "qualification", "budget_signal")
    if budget == "negative":
        _add(10, "Negative budget signal")
    elif budget == "unknown":
        _add(5, "Budget signal unclear")

    # 9. Authority gap.
    authority = _get(
        extracted, "qualification", "authority_signal",
    )
    if authority == "negative":
        _add(8, "Negative authority signal")

    # 10. Timeline slippage.
    timeline = _get(
        extracted, "qualification", "timeline_signal",
    )
    if timeline == "negative":
        _add(10, "Timeline slippage signal")

    # 11. Unresolved objections (5 pts each, max 15).
    objections = _get(
        extracted, "deal_signals", "objections",
    )
    if isinstance(objections, list) and objections:
        obj_pts = min(len(objections) * 5, 15)
        _add(
            obj_pts,
            f"{len(objections)} unresolved objection(s)",
        )

    return min(points, 100), factors


def risk_level(score: int) -> str:
    """Map a numeric score to a risk level label."""
    if score <= 25:
        return "low"
    if score <= 50:
        return "medium"
    if score <= 75:
        return "high"
    return "critical"
