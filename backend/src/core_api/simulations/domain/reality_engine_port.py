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
