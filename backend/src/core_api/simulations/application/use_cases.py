"""Application use cases for the simulations bounded context.

`RunSimulationUseCase` is the one place in Core API that ties three
bounded contexts together: it reads a `Decision` (decisions), reads the
user's active `Goal`s (goals) to pass as context, calls the Reality Engine
(via the `RealityEngineClient` port), and persists the result as a
`Simulation`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from core_api.decisions.domain.entities import Decision, DecisionStatus
from core_api.decisions.domain.exceptions import DecisionNotFoundError
from core_api.decisions.domain.repositories import DecisionRepository
from core_api.goals.domain.repositories import GoalRepository
from core_api.simulations.domain.entities import Simulation, SimulationScenario, SimulationStatus
from core_api.simulations.domain.exceptions import SimulationNotFoundError
from core_api.simulations.domain.reality_engine_port import RealityEngineClient, RealityEngineError
from core_api.simulations.domain.repositories import SimulationRepository

_PIPELINE_VERSION = "reality-engine-agents-0-10"


@dataclass(frozen=True, slots=True)
class RunSimulationInput:
    decision_id: UUID
    requesting_user_id: UUID


class RunSimulationUseCase:
    def __init__(
        self,
        decision_repository: DecisionRepository,
        goal_repository: GoalRepository,
        simulation_repository: SimulationRepository,
        reality_engine_client: RealityEngineClient,
    ) -> None:
        self._decisions = decision_repository
        self._goals = goal_repository
        self._simulations = simulation_repository
        self._reality_engine = reality_engine_client

    async def execute(self, data: RunSimulationInput) -> Simulation:
        decision = await self._get_owned_decision(data.decision_id, data.requesting_user_id)
        decision = await self._advance_to_simulating(decision)

        active_goals = await self._goals.list_for_user(data.requesting_user_id, active_only=True)
        declared_goal_names = [goal.name for goal in active_goals]

        started_at = datetime.now(UTC)
        try:
            outcome = await self._reality_engine.simulate(decision.raw_input, declared_goal_names)
        except RealityEngineError:
            return await self._simulations.create(
                Simulation(
                    id=uuid4(),
                    decision_id=decision.id,
                    status=SimulationStatus.FAILED,
                    pipeline_version=_PIPELINE_VERSION,
                    safety_gate_result={},
                    scenarios=(),
                    synthesis_text=None,
                    reflective_question=None,
                    started_at=started_at,
                    completed_at=datetime.now(UTC),
                )
            )

        if not outcome.safe_to_proceed or not outcome.scenarios:
            # The decision is deliberately left in `simulating` rather than
            # advanced or reverted: what should happen to a decision whose
            # simulation was safety-halted is a product decision this
            # module doesn't make unilaterally (see docs/PRD.md §18).
            return await self._simulations.create(
                Simulation(
                    id=uuid4(),
                    decision_id=decision.id,
                    status=SimulationStatus.PARTIAL,
                    pipeline_version=_PIPELINE_VERSION,
                    safety_gate_result=outcome.safety_gate_result,
                    scenarios=(),
                    synthesis_text=None,
                    reflective_question=None,
                    started_at=started_at,
                    completed_at=datetime.now(UTC),
                )
            )

        scenarios = tuple(
            SimulationScenario(
                id=uuid4(),
                external_id=scenario.id,
                title=scenario.title,
                narrative=scenario.narrative,
                assumptions=scenario.assumptions,
                relative_probability=scenario.relative_probability,
                time_horizon_months=scenario.time_horizon_months,
                goal_alignment_scores=scenario.goal_alignment_scores,
                risk_score=scenario.risk_score,
                reversibility_score=scenario.reversibility_score,
                final_score=scenario.final_score,
                rank=scenario.rank,
            )
            for scenario in outcome.scenarios
        )
        simulation = await self._simulations.create(
            Simulation(
                id=uuid4(),
                decision_id=decision.id,
                status=SimulationStatus.COMPLETED,
                pipeline_version=_PIPELINE_VERSION,
                safety_gate_result=outcome.safety_gate_result,
                scenarios=scenarios,
                synthesis_text=outcome.synthesis_text,
                reflective_question=outcome.reflective_question,
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )
        )

        completed_decision = decision.with_status(DecisionStatus.COMPLETED, at=datetime.now(UTC))
        await self._decisions.update(completed_decision)

        return simulation

    async def _get_owned_decision(self, decision_id: UUID, user_id: UUID) -> Decision:
        decision = await self._decisions.get_by_id(decision_id)
        if decision is None or decision.user_id != user_id:
            raise DecisionNotFoundError(decision_id)
        return decision

    async def _advance_to_simulating(self, decision: Decision) -> Decision:
        # `draft` needs an intermediate hop through `clarifying` (the
        # decision entity's own state machine doesn't allow draft ->
        # simulating directly, see decisions/domain/entities.py). Any
        # other non-`clarifying` status (already simulating, completed,
        # archived) makes the final `with_status` call below raise
        # `InvalidStatusTransitionError` on its own — reusing the
        # aggregate's own invariant instead of duplicating it here.
        now = datetime.now(UTC)
        if decision.status == DecisionStatus.DRAFT:
            decision = await self._decisions.update(
                decision.with_status(DecisionStatus.CLARIFYING, at=now)
            )
        return await self._decisions.update(
            decision.with_status(DecisionStatus.SIMULATING, at=now)
        )


class ListSimulationsForDecisionUseCase:
    def __init__(
        self, decision_repository: DecisionRepository, simulation_repository: SimulationRepository
    ) -> None:
        self._decisions = decision_repository
        self._simulations = simulation_repository

    async def execute(self, decision_id: UUID, requesting_user_id: UUID) -> list[Simulation]:
        decision = await self._decisions.get_by_id(decision_id)
        if decision is None or decision.user_id != requesting_user_id:
            raise DecisionNotFoundError(decision_id)
        return await self._simulations.list_for_decision(decision_id)


class GetSimulationUseCase:
    def __init__(
        self, decision_repository: DecisionRepository, simulation_repository: SimulationRepository
    ) -> None:
        self._decisions = decision_repository
        self._simulations = simulation_repository

    async def execute(self, simulation_id: UUID, requesting_user_id: UUID) -> Simulation:
        simulation = await self._simulations.get_by_id(simulation_id)
        if simulation is None:
            raise SimulationNotFoundError(simulation_id)
        decision = await self._decisions.get_by_id(simulation.decision_id)
        if decision is None or decision.user_id != requesting_user_id:
            raise SimulationNotFoundError(simulation_id)
        return simulation
