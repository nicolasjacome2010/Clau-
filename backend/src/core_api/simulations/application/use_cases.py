"""Application use cases for the simulations bounded context.

`RunSimulationUseCase` is the one place in Core API that ties four
bounded contexts together: it reads a `Decision` (decisions), reads the
user's active `Goal`s (goals) to pass as context, calls the Reality Engine
(via the `RealityEngineClient` port), persists the result as a
`Simulation`, and — when Reality Engine's Agent 11 (Memoria) produced one —
persists the run's semantic memory (memory).

`ReportDecisionOutcomeUseCase` closes the loop (docs/PRD.md CU8): it sends
a past Simulation's scenarios back to Reality Engine's Agent 12
(Aprendizaje) alongside what actually happened, and persists both the
resulting `DecisionOutcome` and its effect on the user's `UserBiasProfile`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from core_api.decisions.domain.entities import Decision, DecisionStatus
from core_api.decisions.domain.exceptions import DecisionNotFoundError
from core_api.decisions.domain.repositories import DecisionRepository
from core_api.goals.domain.repositories import GoalRepository
from core_api.memory.application.use_cases import StoreMemoryInput, StoreMemoryUseCase
from core_api.memory.domain.entities import UserBiasProfile
from core_api.memory.domain.repositories import MemoryEmbeddingRepository, UserBiasProfileRepository
from core_api.simulations.domain.entities import (
    DecisionOutcome,
    Simulation,
    SimulationScenario,
    SimulationStatus,
)
from core_api.simulations.domain.exceptions import (
    DecisionOutcomeAlreadyReportedError,
    NoCompletedSimulationError,
    SimulationNotFoundError,
)
from core_api.simulations.domain.reality_engine_port import (
    RealityEngineCalibrationScenario,
    RealityEngineClient,
    RealityEngineError,
    RealityEngineRankedScenario,
)
from core_api.simulations.domain.repositories import DecisionOutcomeRepository, SimulationRepository

_PIPELINE_VERSION = "reality-engine-agents-0-11"


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
        memory_repository: MemoryEmbeddingRepository,
    ) -> None:
        self._decisions = decision_repository
        self._goals = goal_repository
        self._simulations = simulation_repository
        self._reality_engine = reality_engine_client
        self._memories = memory_repository

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

        if outcome.memory_summary is not None and outcome.memory_embedding is not None:
            # Storing memory is an enhancement on top of a completed
            # simulation, never a precondition of it — same posture Reality
            # Engine's own SimulationPipeline takes toward Agent 11
            # (reality_engine/pipeline/orchestrator.py). Nothing here can
            # fail except a genuine bug (the decision was already validated
            # as owned above), so no defensive try/except is added.
            await StoreMemoryUseCase(self._memories, self._decisions).execute(
                StoreMemoryInput(
                    user_id=data.requesting_user_id,
                    summary_text=outcome.memory_summary,
                    embedding=outcome.memory_embedding,
                    decision_id=decision.id,
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


@dataclass(frozen=True, slots=True)
class ReportDecisionOutcomeInput:
    decision_id: UUID
    requesting_user_id: UUID
    reported_outcome: str


class ReportDecisionOutcomeUseCase:
    def __init__(
        self,
        decision_repository: DecisionRepository,
        simulation_repository: SimulationRepository,
        decision_outcome_repository: DecisionOutcomeRepository,
        user_bias_profile_repository: UserBiasProfileRepository,
        reality_engine_client: RealityEngineClient,
    ) -> None:
        self._decisions = decision_repository
        self._simulations = simulation_repository
        self._outcomes = decision_outcome_repository
        self._profiles = user_bias_profile_repository
        self._reality_engine = reality_engine_client

    async def execute(self, data: ReportDecisionOutcomeInput) -> DecisionOutcome:
        decision = await self._decisions.get_by_id(data.decision_id)
        if decision is None or decision.user_id != data.requesting_user_id:
            raise DecisionNotFoundError(data.decision_id)

        # Checked before anything expensive happens: an already-closed loop
        # must not spend a Reality Engine call, and must never fold a second
        # copy of the same observation into the user's bias profile (see
        # `DecisionOutcomeAlreadyReportedError`).
        existing = await self._outcomes.get_by_decision_id(data.decision_id)
        if existing is not None:
            raise DecisionOutcomeAlreadyReportedError(data.decision_id)

        simulations = await self._simulations.list_for_decision(data.decision_id)
        completed = [s for s in simulations if s.status == SimulationStatus.COMPLETED]
        if not completed:
            raise NoCompletedSimulationError(data.decision_id)
        latest = max(completed, key=lambda s: s.started_at)

        original_scenarios = [
            RealityEngineCalibrationScenario(
                id=s.external_id,
                title=s.title,
                narrative=s.narrative,
                assumptions=s.assumptions,
                relative_probability=s.relative_probability,
                time_horizon_months=s.time_horizon_months,
            )
            for s in latest.scenarios
        ]
        original_ranking = [
            RealityEngineRankedScenario(
                scenario_id=s.external_id, final_score=s.final_score, rank=s.rank
            )
            for s in latest.scenarios
        ]

        calibration = await self._reality_engine.calibrate(
            data.reported_outcome, original_scenarios, original_ranking
        )

        # Reality Engine only knows its own run-scoped `external_id`; the
        # translation back to our internal `SimulationScenario.id` (and the
        # deliberate `None` when Agent 12 found no match — docs/REALITY_
        # ENGINE.md's "blind spot", never forced) happens only here.
        closest_scenario_id = next(
            (s.id for s in latest.scenarios if s.external_id == calibration.closest_scenario_id),
            None,
        )

        outcome = await self._outcomes.create(
            DecisionOutcome(
                id=uuid4(),
                decision_id=decision.id,
                reported_outcome=data.reported_outcome,
                closest_scenario_id=closest_scenario_id,
                calibration_delta=calibration.calibration_delta,
                system_errors_identified=calibration.system_errors_identified,
                reported_at=datetime.now(UTC),
            )
        )

        current_profile = await self._profiles.get_by_user_id(data.requesting_user_id)
        if current_profile is None:
            current_profile = UserBiasProfile(user_id=data.requesting_user_id)
        now = datetime.now(UTC)
        updated_profile = current_profile.with_calibration_delta(
            calibration.calibration_delta, at=now
        )
        for bias, confidence in calibration.user_bias_profile_update.items():
            # Reality Engine's `CalibrationOutput.user_bias_profile_update`
            # has no range constraint on its values, but `BiasObservation`
            # requires a 0..1 confidence — clamp defensively rather than
            # letting a borderline model output raise deep inside `with_
            # bias_observation` and lose the whole calibration.
            clamped_confidence = max(0.0, min(1.0, confidence))
            updated_profile = updated_profile.with_bias_observation(
                bias, clamped_confidence, at=now
            )
        await self._profiles.upsert(updated_profile)

        return outcome


class ListDecisionOutcomesUseCase:
    """Every closed loop belonging to the caller, in two queries.

    This exists so a client can tell which of its decisions have already
    been closed *without* asking per decision: the only alternative the API
    offered was `POST .../outcome`, which reports rather than reads, so a
    UI wanting that state had no honest way to get it (docs/UX_DESIGN.md
    Pantalla 10's ">60 días sin cerrar el ciclo" indicator, and Pantalla
    11's own prompt).

    Ownership is resolved here, in the use case, rather than by joining
    `decisions` from inside `DecisionOutcomeRepository` — same rule as
    `RunSimulationUseCase`: cross-context coupling is visible at the
    constructor, never hidden inside a repository.
    """

    def __init__(
        self,
        decision_repository: DecisionRepository,
        decision_outcome_repository: DecisionOutcomeRepository,
    ) -> None:
        self._decisions = decision_repository
        self._outcomes = decision_outcome_repository

    async def execute(self, requesting_user_id: UUID) -> list[DecisionOutcome]:
        decisions = await self._decisions.list_for_user(requesting_user_id)
        return await self._outcomes.list_for_decisions([d.id for d in decisions])
