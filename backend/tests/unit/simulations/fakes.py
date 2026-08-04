"""In-memory/fake doubles for the simulations bounded context, used only
by unit tests.
"""

from __future__ import annotations

from uuid import UUID

from core_api.simulations.domain.entities import Simulation
from core_api.simulations.domain.reality_engine_port import (
    RealityEngineClient,
    RealityEngineError,
    RealityEngineSimulationOutcome,
)
from core_api.simulations.domain.repositories import SimulationRepository


class InMemorySimulationRepository(SimulationRepository):
    def __init__(self) -> None:
        self._simulations: dict[UUID, Simulation] = {}

    async def get_by_id(self, simulation_id: UUID) -> Simulation | None:
        return self._simulations.get(simulation_id)

    async def list_for_decision(self, decision_id: UUID) -> list[Simulation]:
        return [s for s in self._simulations.values() if s.decision_id == decision_id]

    async def create(self, simulation: Simulation) -> Simulation:
        self._simulations[simulation.id] = simulation
        return simulation


class FakeRealityEngineClient(RealityEngineClient):
    """Returns canned outcomes/errors from `responses`, in order — same
    pattern as reality_engine's own `FakeLLMProvider`.
    """

    def __init__(
        self, responses: list[RealityEngineSimulationOutcome | RealityEngineError] | None = None
    ) -> None:
        self._responses = list(responses or [])
        self.calls: list[tuple[str, list[str]]] = []

    async def simulate(
        self, raw_input: str, declared_goals: list[str]
    ) -> RealityEngineSimulationOutcome:
        self.calls.append((raw_input, declared_goals))
        if not self._responses:
            raise RealityEngineError("FakeRealityEngineClient has no more canned responses")
        result = self._responses.pop(0)
        if isinstance(result, RealityEngineError):
            raise result
        return result
