"""Structured I/O contracts for pipeline agents.

Pydantic models, not dataclasses: they double as the JSON Schema handed to
`AIGateway.generate_structured` (docs/REALITY_ENGINE.md §2 — every agent's
output is validated JSON, never free text).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class RiskLevel(StrEnum):
    NONE = "none"
    MODERATE_DISTRESS = "moderate_distress"
    ACUTE_RISK = "acute_risk"


class RecommendedAction(StrEnum):
    PROCEED = "proceed"
    PROCEED_WITH_CARE = "proceed_with_care"
    HALT_AND_REFER = "halt_and_refer"


class SafetyGateOutput(BaseModel):
    """docs/REALITY_ENGINE.md §2, Agente 0 — Risk & Safety Gate."""

    risk_level: RiskLevel
    signals_detected: list[str] = Field(default_factory=list)
    safe_to_proceed: bool
    recommended_action: RecommendedAction
