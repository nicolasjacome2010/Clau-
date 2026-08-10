"""SQLAlchemy implementation of the simulations domain repository."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_api.simulations.domain.entities import (
    DecisionOutcome,
    Simulation,
    SimulationScenario,
    SimulationStatus,
)
from core_api.simulations.domain.repositories import DecisionOutcomeRepository, SimulationRepository
from core_api.simulations.infrastructure.models import (
    DecisionOutcomeModel,
    SimulationModel,
    SimulationScenarioModel,
)


def _to_scenario_entity(model: SimulationScenarioModel) -> SimulationScenario:
    return SimulationScenario(
        id=model.id,
        external_id=model.external_id,
        title=model.title,
        narrative=model.narrative,
        assumptions=list(model.assumptions),
        relative_probability=float(model.relative_probability),
        time_horizon_months=model.time_horizon_months,
        goal_alignment_scores=list(model.goal_alignment_scores),
        risk_score=float(model.risk_score),
        reversibility_score=float(model.reversibility_score),
        final_score=float(model.final_score),
        rank=model.rank,
    )


class SqlAlchemySimulationRepository(SimulationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _to_entity(self, model: SimulationModel) -> Simulation:
        result = await self._session.execute(
            select(SimulationScenarioModel)
            .where(SimulationScenarioModel.simulation_id == model.id)
            .order_by(SimulationScenarioModel.rank)
        )
        scenarios = tuple(_to_scenario_entity(row) for row in result.scalars().all())
        return Simulation(
            id=model.id,
            decision_id=model.decision_id,
            status=SimulationStatus(model.status),
            pipeline_version=model.pipeline_version,
            safety_gate_result=dict(model.safety_gate_result),
            scenarios=scenarios,
            synthesis_text=model.synthesis_text,
            reflective_question=model.reflective_question,
            started_at=model.started_at,
            completed_at=model.completed_at,
        )

    async def get_by_id(self, simulation_id: UUID) -> Simulation | None:
        model = await self._session.get(SimulationModel, simulation_id)
        return await self._to_entity(model) if model else None

    async def list_for_decision(self, decision_id: UUID) -> list[Simulation]:
        result = await self._session.execute(
            select(SimulationModel)
            .where(SimulationModel.decision_id == decision_id)
            .order_by(SimulationModel.started_at.desc())
        )
        return [await self._to_entity(model) for model in result.scalars().all()]

    async def create(self, simulation: Simulation) -> Simulation:
        model = SimulationModel(
            id=simulation.id,
            decision_id=simulation.decision_id,
            status=simulation.status.value,
            pipeline_version=simulation.pipeline_version,
            safety_gate_result=simulation.safety_gate_result,
            synthesis_text=simulation.synthesis_text,
            reflective_question=simulation.reflective_question,
            started_at=simulation.started_at,
            completed_at=simulation.completed_at,
        )
        self._session.add(model)
        for scenario in simulation.scenarios:
            self._session.add(
                SimulationScenarioModel(
                    id=scenario.id,
                    simulation_id=simulation.id,
                    external_id=scenario.external_id,
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
            )
        await self._session.flush()
        return await self._to_entity(model)


def _to_outcome_entity(model: DecisionOutcomeModel) -> DecisionOutcome:
    return DecisionOutcome(
        id=model.id,
        decision_id=model.decision_id,
        reported_outcome=model.reported_outcome,
        closest_scenario_id=model.closest_scenario_id,
        calibration_delta=float(model.calibration_delta),
        system_errors_identified=list(model.system_errors_identified),
        reported_at=model.reported_at,
    )


class SqlAlchemyDecisionOutcomeRepository(DecisionOutcomeRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_decision_id(self, decision_id: UUID) -> DecisionOutcome | None:
        result = await self._session.execute(
            select(DecisionOutcomeModel).where(DecisionOutcomeModel.decision_id == decision_id)
        )
        model = result.scalars().first()
        return _to_outcome_entity(model) if model else None

    async def list_for_decisions(self, decision_ids: Sequence[UUID]) -> list[DecisionOutcome]:
        if not decision_ids:
            # `IN ()` is a syntax error in some dialects and always an empty
            # result in the rest — skip the round trip entirely.
            return []
        result = await self._session.execute(
            select(DecisionOutcomeModel).where(
                DecisionOutcomeModel.decision_id.in_(decision_ids)
            )
        )
        return [_to_outcome_entity(model) for model in result.scalars().all()]

    async def create(self, outcome: DecisionOutcome) -> DecisionOutcome:
        model = DecisionOutcomeModel(
            id=outcome.id,
            decision_id=outcome.decision_id,
            reported_outcome=outcome.reported_outcome,
            closest_scenario_id=outcome.closest_scenario_id,
            calibration_delta=outcome.calibration_delta,
            system_errors_identified=outcome.system_errors_identified,
            reported_at=outcome.reported_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _to_outcome_entity(model)
