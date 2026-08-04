"""HTTP API for the simulations bounded context.

Simulations are scoped to "my decisions" — every endpoint checks decision
(or, for the standalone detail endpoint, simulation-via-decision)
ownership against the caller's JWT identity before returning anything
(see goals/api/router.py for the same convention).
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from core_api.decisions.domain.exceptions import DecisionNotFoundError
from core_api.decisions.domain.repositories import DecisionRepository
from core_api.dependencies import (
    get_current_identity,
    get_decision_outcome_repository,
    get_decision_repository,
    get_goal_repository,
    get_memory_embedding_repository,
    get_reality_engine_client,
    get_simulation_repository,
    get_user_bias_profile_repository,
)
from core_api.goals.domain.repositories import GoalRepository
from core_api.identity.application.use_cases import AuthenticatedIdentity
from core_api.memory.domain.repositories import MemoryEmbeddingRepository, UserBiasProfileRepository
from core_api.simulations.api.schemas import (
    DecisionOutcomeResponse,
    ReportDecisionOutcomeRequest,
    SimulationResponse,
    SimulationScenarioResponse,
)
from core_api.simulations.application.use_cases import (
    GetSimulationUseCase,
    ListSimulationsForDecisionUseCase,
    ReportDecisionOutcomeInput,
    ReportDecisionOutcomeUseCase,
    RunSimulationInput,
    RunSimulationUseCase,
)
from core_api.simulations.domain.entities import DecisionOutcome, Simulation
from core_api.simulations.domain.exceptions import (
    NoCompletedSimulationError,
    SimulationNotFoundError,
)
from core_api.simulations.domain.reality_engine_port import RealityEngineClient, RealityEngineError
from core_api.simulations.domain.repositories import DecisionOutcomeRepository, SimulationRepository

router = APIRouter(prefix="/v1", tags=["simulations"])


def _to_response(simulation: Simulation) -> SimulationResponse:
    return SimulationResponse(
        id=simulation.id,
        decision_id=simulation.decision_id,
        status=simulation.status.value,
        pipeline_version=simulation.pipeline_version,
        safety_gate_result=simulation.safety_gate_result,
        scenarios=[
            SimulationScenarioResponse(
                id=s.id,
                title=s.title,
                narrative=s.narrative,
                assumptions=s.assumptions,
                relative_probability=s.relative_probability,
                time_horizon_months=s.time_horizon_months,
                goal_alignment_scores=s.goal_alignment_scores,
                risk_score=s.risk_score,
                reversibility_score=s.reversibility_score,
                final_score=s.final_score,
                rank=s.rank,
            )
            for s in simulation.scenarios
        ],
        synthesis_text=simulation.synthesis_text,
        reflective_question=simulation.reflective_question,
        started_at=simulation.started_at,
        completed_at=simulation.completed_at,
    )


@router.post(
    "/decisions/{decision_id}/simulations",
    response_model=SimulationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def run_simulation(
    decision_id: UUID,
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    decision_repository: Annotated[DecisionRepository, Depends(get_decision_repository)],
    goal_repository: Annotated[GoalRepository, Depends(get_goal_repository)],
    simulation_repository: Annotated[SimulationRepository, Depends(get_simulation_repository)],
    reality_engine_client: Annotated[RealityEngineClient, Depends(get_reality_engine_client)],
    memory_repository: Annotated[
        MemoryEmbeddingRepository, Depends(get_memory_embedding_repository)
    ],
) -> SimulationResponse:
    use_case = RunSimulationUseCase(
        decision_repository,
        goal_repository,
        simulation_repository,
        reality_engine_client,
        memory_repository,
    )
    try:
        simulation = await use_case.execute(
            RunSimulationInput(decision_id=decision_id, requesting_user_id=identity.id)
        )
    except DecisionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found"
        ) from exc
    return _to_response(simulation)


@router.get("/decisions/{decision_id}/simulations", response_model=list[SimulationResponse])
async def list_simulations_for_decision(
    decision_id: UUID,
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    decision_repository: Annotated[DecisionRepository, Depends(get_decision_repository)],
    simulation_repository: Annotated[SimulationRepository, Depends(get_simulation_repository)],
) -> list[SimulationResponse]:
    use_case = ListSimulationsForDecisionUseCase(decision_repository, simulation_repository)
    try:
        simulations = await use_case.execute(decision_id, identity.id)
    except DecisionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found"
        ) from exc
    return [_to_response(s) for s in simulations]


@router.get("/simulations/{simulation_id}", response_model=SimulationResponse)
async def get_simulation(
    simulation_id: UUID,
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    decision_repository: Annotated[DecisionRepository, Depends(get_decision_repository)],
    simulation_repository: Annotated[SimulationRepository, Depends(get_simulation_repository)],
) -> SimulationResponse:
    use_case = GetSimulationUseCase(decision_repository, simulation_repository)
    try:
        simulation = await use_case.execute(simulation_id, identity.id)
    except SimulationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found"
        ) from exc
    return _to_response(simulation)


def _to_outcome_response(outcome: DecisionOutcome) -> DecisionOutcomeResponse:
    return DecisionOutcomeResponse(
        id=outcome.id,
        decision_id=outcome.decision_id,
        reported_outcome=outcome.reported_outcome,
        closest_scenario_id=outcome.closest_scenario_id,
        calibration_delta=outcome.calibration_delta,
        system_errors_identified=outcome.system_errors_identified,
        reported_at=outcome.reported_at,
    )


@router.post(
    "/decisions/{decision_id}/outcome",
    response_model=DecisionOutcomeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def report_decision_outcome(
    decision_id: UUID,
    payload: ReportDecisionOutcomeRequest,
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    decision_repository: Annotated[DecisionRepository, Depends(get_decision_repository)],
    simulation_repository: Annotated[SimulationRepository, Depends(get_simulation_repository)],
    decision_outcome_repository: Annotated[
        DecisionOutcomeRepository, Depends(get_decision_outcome_repository)
    ],
    user_bias_profile_repository: Annotated[
        UserBiasProfileRepository, Depends(get_user_bias_profile_repository)
    ],
    reality_engine_client: Annotated[RealityEngineClient, Depends(get_reality_engine_client)],
) -> DecisionOutcomeResponse:
    use_case = ReportDecisionOutcomeUseCase(
        decision_repository,
        simulation_repository,
        decision_outcome_repository,
        user_bias_profile_repository,
        reality_engine_client,
    )
    try:
        outcome = await use_case.execute(
            ReportDecisionOutcomeInput(
                decision_id=decision_id,
                requesting_user_id=identity.id,
                reported_outcome=payload.reported_outcome,
            )
        )
    except DecisionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found"
        ) from exc
    except NoCompletedSimulationError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Decision has no completed simulation to report against",
        ) from exc
    except RealityEngineError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Calibration is temporarily unavailable",
        ) from exc
    return _to_outcome_response(outcome)
