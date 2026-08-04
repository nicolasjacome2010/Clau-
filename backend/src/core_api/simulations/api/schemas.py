"""Pydantic request/response DTOs for the simulations HTTP API."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class SimulationScenarioResponse(BaseModel):
    id: UUID
    title: str
    narrative: str
    assumptions: list[str]
    relative_probability: float
    time_horizon_months: int
    goal_alignment_scores: list[dict[str, Any]]
    risk_score: float
    reversibility_score: float
    final_score: float
    rank: int


class SimulationResponse(BaseModel):
    id: UUID
    decision_id: UUID
    status: str
    pipeline_version: str
    safety_gate_result: dict[str, Any]
    scenarios: list[SimulationScenarioResponse]
    synthesis_text: str | None
    reflective_question: str | None
    started_at: datetime
    completed_at: datetime | None


class ReportDecisionOutcomeRequest(BaseModel):
    reported_outcome: str


class DecisionOutcomeResponse(BaseModel):
    id: UUID
    decision_id: UUID
    reported_outcome: str
    closest_scenario_id: UUID | None
    calibration_delta: float
    system_errors_identified: list[str]
    reported_at: datetime
