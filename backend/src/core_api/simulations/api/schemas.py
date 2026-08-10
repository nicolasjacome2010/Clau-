"""Pydantic request/response DTOs for the simulations HTTP API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
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


class SimulationStreamStageResponse(BaseModel):
    """One NDJSON line of `POST /decisions/{id}/simulations/stream` while
    the run is in progress — a direct relay of `SimulationStageEvent`.
    """

    type: Literal["stage"] = "stage"
    stage: str
    status: str


class SimulationStreamResultResponse(BaseModel):
    """The stream's last line: the same body `run_simulation` returns
    synchronously, wrapped so the client can tell it apart from a stage
    line without inspecting its shape.
    """

    type: Literal["result"] = "result"
    result: SimulationResponse


class SimulationStreamErrorResponse(BaseModel):
    """Emitted only if the run fails *after* the stream's 200 has already
    gone out — by then an HTTP error status is no longer possible, so the
    failure has to be said in-band instead of leaving a body that ends
    early and reads exactly like a dropped connection.
    """

    type: Literal["error"] = "error"
    message: str


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
