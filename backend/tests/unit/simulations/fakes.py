"""In-memory/fake doubles for the simulations bounded context, used only
by unit tests.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from uuid import UUID

from core_api.simulations.domain.entities import DecisionOutcome, Simulation
from core_api.simulations.domain.reality_engine_port import (
    RealityEngineCalibrationOutcome,
    RealityEngineCalibrationScenario,
    RealityEngineClient,
    RealityEngineError,
    RealityEngineRankedScenario,
    RealityEngineSimulationOutcome,
    RealityEngineStageEvent,
)
from core_api.simulations.domain.repositories import DecisionOutcomeRepository, SimulationRepository


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


class InMemoryDecisionOutcomeRepository(DecisionOutcomeRepository):
    def __init__(self) -> None:
        self._outcomes: dict[UUID, DecisionOutcome] = {}

    async def get_by_decision_id(self, decision_id: UUID) -> DecisionOutcome | None:
        return next(
            (o for o in self._outcomes.values() if o.decision_id == decision_id), None
        )

    async def list_for_decisions(self, decision_ids: Sequence[UUID]) -> list[DecisionOutcome]:
        wanted = set(decision_ids)
        return [o for o in self._outcomes.values() if o.decision_id in wanted]

    async def create(self, outcome: DecisionOutcome) -> DecisionOutcome:
        self._outcomes[outcome.id] = outcome
        return outcome


class FakeRealityEngineClient(RealityEngineClient):
    """Returns canned outcomes/errors from `responses`/`calibrate_responses`,
    in order — same pattern as reality_engine's own `FakeLLMProvider`.
    """

    def __init__(
        self,
        responses: list[RealityEngineSimulationOutcome | RealityEngineError] | None = None,
        calibrate_responses: list[RealityEngineCalibrationOutcome | RealityEngineError]
        | None = None,
        stream_events: list[RealityEngineStageEvent] | None = None,
    ) -> None:
        self._responses = list(responses or [])
        self._calibrate_responses = list(calibrate_responses or [])
        # Canned progress events for `simulate_stream` — shared across every
        # call, since tests care about "does the caller relay these", not
        # about varying them run to run.
        self._stream_events = list(stream_events or [])
        self.calls: list[tuple[str, list[str]]] = []
        self.stream_calls: list[tuple[str, list[str]]] = []
        self.calibrate_calls: list[
            tuple[str, list[RealityEngineCalibrationScenario], list[RealityEngineRankedScenario]]
        ] = []

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

    async def simulate_stream(
        self, raw_input: str, declared_goals: list[str]
    ) -> AsyncIterator[RealityEngineStageEvent | RealityEngineSimulationOutcome]:
        self.stream_calls.append((raw_input, declared_goals))
        for event in self._stream_events:
            yield event
        if not self._responses:
            raise RealityEngineError("FakeRealityEngineClient has no more canned responses")
        result = self._responses.pop(0)
        if isinstance(result, RealityEngineError):
            raise result
        yield result

    async def calibrate(
        self,
        reported_outcome: str,
        original_scenarios: list[RealityEngineCalibrationScenario],
        original_ranking: list[RealityEngineRankedScenario],
    ) -> RealityEngineCalibrationOutcome:
        self.calibrate_calls.append((reported_outcome, original_scenarios, original_ranking))
        if not self._calibrate_responses:
            raise RealityEngineError(
                "FakeRealityEngineClient has no more canned calibrate responses"
            )
        result = self._calibrate_responses.pop(0)
        if isinstance(result, RealityEngineError):
            raise result
        return result
