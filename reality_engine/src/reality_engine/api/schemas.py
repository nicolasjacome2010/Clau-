"""Pydantic request/response DTOs for the Reality Engine HTTP API."""

from __future__ import annotations

from pydantic import BaseModel, Field

from reality_engine.pipeline.domain.schemas import RecommendedAction, RiskLevel


class SafetyCheckRequest(BaseModel):
    raw_input: str = Field(min_length=1, max_length=4000)


class SafetyCheckResponse(BaseModel):
    risk_level: RiskLevel
    signals_detected: list[str]
    safe_to_proceed: bool
    recommended_action: RecommendedAction
