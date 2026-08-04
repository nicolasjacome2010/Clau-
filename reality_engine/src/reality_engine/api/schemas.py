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


class AnalyzeRequest(BaseModel):
    raw_input: str = Field(min_length=1, max_length=4000)
    declared_goals: list[str] = Field(default_factory=list, max_length=5)


class CalibrateScenarioRequest(BaseModel):
    """Mirrors `pipeline.domain.schemas.Scenario` — the caller (Core API's
    `simulations` module) reconstructs this from the `Simulation` it stored
    for the decision being reported on.
    """

    id: str
    title: str
    narrative: str
    based_on_option: str = ""
    assumptions: list[str] = Field(default_factory=list)
    relative_probability: float = Field(ge=0, le=100)
    time_horizon_months: int = Field(ge=1, le=60)


class CalibrateRankedScenarioRequest(BaseModel):
    scenario_id: str
    final_score: float
    rank: int


class CalibrateRequest(BaseModel):
    reported_outcome: str = Field(min_length=1, max_length=4000)
    original_scenarios: list[CalibrateScenarioRequest] = Field(min_length=3, max_length=5)
    original_ranking: list[CalibrateRankedScenarioRequest] = Field(default_factory=list)


class CalibrateResponse(BaseModel):
    closest_scenario_id: str | None
    calibration_delta: float
    system_errors_identified: list[str]
    user_bias_profile_update: dict[str, float]
