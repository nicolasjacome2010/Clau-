"""SQLAlchemy implementation of the simulations domain repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_api.simulations.domain.entities import Simulation, SimulationScenario, SimulationStatus
from core_api.simulations.domain.repositories import SimulationRepository
from core_api.simulations.infrastructure.models import SimulationModel, SimulationScenarioModel


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
