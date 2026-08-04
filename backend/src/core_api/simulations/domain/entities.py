"""Domain entities for the simulations bounded context.

A Simulation is one run of the Reality Engine pipeline against a Decision
(docs/DATABASE.md §2.5). It's immutable once created — re-simulating a
Decision creates a new Simulation row, it never mutates an old one, so
there is no `update` in the repository interface (see repositories.py).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class SimulationStatus(StrEnum):
    """A subset of docs/DATABASE.md §2.5's status enum: `queued`/`running`
    aren't reachable yet because this module calls the Reality Engine
    synchronously (no queue — see reality_engine_port.py's docstring), so a
    Simulation is only ever created already in a terminal state.
    """

    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class SimulationScenario:
    id: UUID
    external_id: str
    """The scenario id Reality Engine assigned within this run — not
    globally unique, only unique within one Simulation's `scenarios`.
    """
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


@dataclass(frozen=True, slots=True)
class Simulation:
    id: UUID
    decision_id: UUID
    status: SimulationStatus
    pipeline_version: str
    safety_gate_result: dict[str, Any]
    scenarios: tuple[SimulationScenario, ...]
    synthesis_text: str | None
    reflective_question: str | None
    started_at: datetime
    completed_at: datetime | None
