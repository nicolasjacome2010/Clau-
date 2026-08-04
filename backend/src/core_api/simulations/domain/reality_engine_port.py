"""Port for calling the Reality Engine service (docs/ARCHITECTURE.md §2.2).

Core API and Reality Engine are separate deployable services (different
Python projects, different venvs — see CLAUDE.md), so this module defines
its own plain DTOs for what it needs from a simulation run rather than
importing `reality_engine`'s Pydantic models directly. The concrete HTTP
adapter (`infrastructure/reality_engine_client.py`) is the only place that
knows about Reality Engine's actual JSON wire shape; if that shape changes,
only the adapter changes, never this port or any use case.

Synchronous, not queued: `docs/ARCHITECTURE.md §2.2` describes dispatching
simulation requests via a queue so an HTTP request never blocks on a
15-30s pipeline run. This port is called directly and synchronously for
now — the queue-based dispatch is deferred, not built speculatively ahead
of a second caller that would need it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class RealityEngineScenario:
    id: str
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
class RealityEngineSimulationOutcome:
    safe_to_proceed: bool
    safety_gate_result: dict[str, Any]
    scenarios: list[RealityEngineScenario] = field(default_factory=list)
    synthesis_text: str | None = None
    reflective_question: str | None = None
    # Agent 11 (Memoria) output — None whenever Reality Engine had no
    # embedding provider configured or the memory step failed; storing
    # memory is an enhancement, never a reason to fail the whole
    # simulation (see reality_engine/pipeline/orchestrator.py).
    memory_summary: str | None = None
    memory_embedding: tuple[float, ...] | None = None


@dataclass(frozen=True, slots=True)
class RealityEngineCalibrationScenario:
    """What `calibrate()` needs to send back per scenario — the subset of
    a stored `Simulation`'s scenario data Reality Engine's Agent 12 needs
    to reconstruct its own `Scenario` shape.
    """

    id: str
    title: str
    narrative: str
    assumptions: list[str]
    relative_probability: float
    time_horizon_months: int


@dataclass(frozen=True, slots=True)
class RealityEngineRankedScenario:
    scenario_id: str
    final_score: float
    rank: int


@dataclass(frozen=True, slots=True)
class RealityEngineCalibrationOutcome:
    closest_scenario_id: str | None
    calibration_delta: float
    system_errors_identified: list[str]
    user_bias_profile_update: dict[str, float]


class RealityEngineError(Exception):
    """Raised for any failure calling the Reality Engine service: network
    error, non-2xx response, or a response that doesn't match the
    expected shape.
    """


class RealityEngineClient(ABC):
    @abstractmethod
    async def simulate(
        self, raw_input: str, declared_goals: list[str]
    ) -> RealityEngineSimulationOutcome: ...

    @abstractmethod
    async def calibrate(
        self,
        reported_outcome: str,
        original_scenarios: list[RealityEngineCalibrationScenario],
        original_ranking: list[RealityEngineRankedScenario],
    ) -> RealityEngineCalibrationOutcome: ...
