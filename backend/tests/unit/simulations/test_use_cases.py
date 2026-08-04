from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from core_api.decisions.domain.entities import Decision, DecisionStatus, DecisionVertical
from core_api.decisions.domain.entities import (
    InvalidStatusTransitionError as DecisionInvalidTransition,
)
from core_api.decisions.domain.exceptions import DecisionNotFoundError
from core_api.goals.domain.entities import Goal
from core_api.simulations.application.use_cases import (
    GetSimulationUseCase,
    ListSimulationsForDecisionUseCase,
    RunSimulationInput,
    RunSimulationUseCase,
)
from core_api.simulations.domain.entities import SimulationStatus
from core_api.simulations.domain.exceptions import SimulationNotFoundError
from core_api.simulations.domain.reality_engine_port import (
    RealityEngineError,
    RealityEngineScenario,
    RealityEngineSimulationOutcome,
)
from tests.unit.decisions.fakes import InMemoryDecisionRepository
from tests.unit.goals.fakes import InMemoryGoalRepository
from tests.unit.simulations.fakes import FakeRealityEngineClient, InMemorySimulationRepository


async def _make_draft_decision(decisions: InMemoryDecisionRepository, user_id: object) -> Decision:
    now = datetime.now(UTC)
    decision = Decision(
        id=uuid4(),
        user_id=user_id,  # type: ignore[arg-type]
        title="¿Debo aceptar la oferta?",
        vertical=DecisionVertical.CAREER,
        status=DecisionStatus.DRAFT,
        raw_input="¿Debo aceptar la oferta de trabajo en la empresa Z?",
        created_at=now,
        updated_at=now,
    )
    return await decisions.create(decision)


def _safe_outcome() -> RealityEngineSimulationOutcome:
    return RealityEngineSimulationOutcome(
        safe_to_proceed=True,
        safety_gate_result={"risk_level": "none", "recommended_action": "proceed"},
        scenarios=[
            RealityEngineScenario(
                id="a",
                title="Aceptas",
                narrative="Podrías crecer profesionalmente.",
                assumptions=["El mercado se mantiene estable"],
                relative_probability=60,
                time_horizon_months=12,
                goal_alignment_scores=[{"goal": "Estabilidad", "score": 80, "justification": "x"}],
                risk_score=30,
                reversibility_score=50,
                final_score=70,
                rank=1,
            ),
            RealityEngineScenario(
                id="b",
                title="Rechazas",
                narrative="Podrías negociar mejores términos.",
                assumptions=[],
                relative_probability=40,
                time_horizon_months=12,
                goal_alignment_scores=[{"goal": "Estabilidad", "score": 50, "justification": "x"}],
                risk_score=20,
                reversibility_score=80,
                final_score=55,
                rank=2,
            ),
        ],
        synthesis_text="Basado en tus objetivos...",
        reflective_question="¿Qué te preocupa más?",
    )


def _unsafe_outcome() -> RealityEngineSimulationOutcome:
    return RealityEngineSimulationOutcome(
        safe_to_proceed=False,
        safety_gate_result={"risk_level": "acute_risk", "recommended_action": "halt_and_refer"},
    )


@pytest.mark.asyncio
async def test_run_simulation_from_draft_completes_and_advances_decision() -> None:
    decisions = InMemoryDecisionRepository()
    goals = InMemoryGoalRepository()
    simulations = InMemorySimulationRepository()
    reality_engine = FakeRealityEngineClient(responses=[_safe_outcome()])
    user_id = uuid4()
    decision = await _make_draft_decision(decisions, user_id)
    await goals.create(
        Goal(
            id=uuid4(),
            user_id=user_id,
            name="Estabilidad",
            default_weight=70,
            is_active=True,
            created_at=datetime.now(UTC),
        )
    )

    use_case = RunSimulationUseCase(decisions, goals, simulations, reality_engine)
    simulation = await use_case.execute(
        RunSimulationInput(decision_id=decision.id, requesting_user_id=user_id)
    )

    assert simulation.status == SimulationStatus.COMPLETED
    assert len(simulation.scenarios) == 2
    assert simulation.synthesis_text == "Basado en tus objetivos..."
    updated_decision = await decisions.get_by_id(decision.id)
    assert updated_decision is not None
    assert updated_decision.status == DecisionStatus.COMPLETED
    assert reality_engine.calls == [(decision.raw_input, ["Estabilidad"])]


@pytest.mark.asyncio
async def test_run_simulation_unsafe_creates_partial_and_leaves_decision_simulating() -> None:
    decisions = InMemoryDecisionRepository()
    goals = InMemoryGoalRepository()
    simulations = InMemorySimulationRepository()
    reality_engine = FakeRealityEngineClient(responses=[_unsafe_outcome()])
    user_id = uuid4()
    decision = await _make_draft_decision(decisions, user_id)

    use_case = RunSimulationUseCase(decisions, goals, simulations, reality_engine)
    simulation = await use_case.execute(
        RunSimulationInput(decision_id=decision.id, requesting_user_id=user_id)
    )

    assert simulation.status == SimulationStatus.PARTIAL
    assert simulation.scenarios == ()
    updated_decision = await decisions.get_by_id(decision.id)
    assert updated_decision is not None
    assert updated_decision.status == DecisionStatus.SIMULATING


@pytest.mark.asyncio
async def test_run_simulation_reality_engine_failure_creates_failed_simulation() -> None:
    decisions = InMemoryDecisionRepository()
    goals = InMemoryGoalRepository()
    simulations = InMemorySimulationRepository()
    reality_engine = FakeRealityEngineClient(responses=[RealityEngineError("network down")])
    user_id = uuid4()
    decision = await _make_draft_decision(decisions, user_id)

    use_case = RunSimulationUseCase(decisions, goals, simulations, reality_engine)
    simulation = await use_case.execute(
        RunSimulationInput(decision_id=decision.id, requesting_user_id=user_id)
    )

    assert simulation.status == SimulationStatus.FAILED
    updated_decision = await decisions.get_by_id(decision.id)
    assert updated_decision is not None
    assert updated_decision.status == DecisionStatus.SIMULATING


@pytest.mark.asyncio
async def test_run_simulation_raises_when_decision_not_owned() -> None:
    decisions = InMemoryDecisionRepository()
    goals = InMemoryGoalRepository()
    simulations = InMemorySimulationRepository()
    reality_engine = FakeRealityEngineClient()
    owner_id = uuid4()
    decision = await _make_draft_decision(decisions, owner_id)

    use_case = RunSimulationUseCase(decisions, goals, simulations, reality_engine)
    with pytest.raises(DecisionNotFoundError):
        await use_case.execute(
            RunSimulationInput(decision_id=decision.id, requesting_user_id=uuid4())
        )


@pytest.mark.asyncio
async def test_run_simulation_rejects_already_completed_decision() -> None:
    decisions = InMemoryDecisionRepository()
    goals = InMemoryGoalRepository()
    simulations = InMemorySimulationRepository()
    reality_engine = FakeRealityEngineClient()
    user_id = uuid4()
    decision = await _make_draft_decision(decisions, user_id)
    now = datetime.now(UTC)
    archived = decision.with_status(DecisionStatus.CLARIFYING, at=now).with_status(
        DecisionStatus.SIMULATING, at=now
    ).with_status(DecisionStatus.COMPLETED, at=now)
    await decisions.update(archived)

    use_case = RunSimulationUseCase(decisions, goals, simulations, reality_engine)
    with pytest.raises(DecisionInvalidTransition):
        await use_case.execute(
            RunSimulationInput(decision_id=decision.id, requesting_user_id=user_id)
        )


@pytest.mark.asyncio
async def test_list_simulations_for_decision_scoped_to_owner() -> None:
    decisions = InMemoryDecisionRepository()
    goals = InMemoryGoalRepository()
    simulations = InMemorySimulationRepository()
    reality_engine = FakeRealityEngineClient(responses=[_safe_outcome()])
    user_id = uuid4()
    decision = await _make_draft_decision(decisions, user_id)
    await RunSimulationUseCase(decisions, goals, simulations, reality_engine).execute(
        RunSimulationInput(decision_id=decision.id, requesting_user_id=user_id)
    )

    result = await ListSimulationsForDecisionUseCase(decisions, simulations).execute(
        decision.id, user_id
    )
    assert len(result) == 1

    with pytest.raises(DecisionNotFoundError):
        await ListSimulationsForDecisionUseCase(decisions, simulations).execute(
            decision.id, uuid4()
        )


@pytest.mark.asyncio
async def test_get_simulation_raises_when_owning_decision_belongs_to_another_user() -> None:
    decisions = InMemoryDecisionRepository()
    goals = InMemoryGoalRepository()
    simulations = InMemorySimulationRepository()
    reality_engine = FakeRealityEngineClient(responses=[_safe_outcome()])
    user_id = uuid4()
    decision = await _make_draft_decision(decisions, user_id)
    simulation = await RunSimulationUseCase(decisions, goals, simulations, reality_engine).execute(
        RunSimulationInput(decision_id=decision.id, requesting_user_id=user_id)
    )

    fetched = await GetSimulationUseCase(decisions, simulations).execute(simulation.id, user_id)
    assert fetched.id == simulation.id

    with pytest.raises(SimulationNotFoundError):
        await GetSimulationUseCase(decisions, simulations).execute(simulation.id, uuid4())


@pytest.mark.asyncio
async def test_get_simulation_raises_when_simulation_does_not_exist() -> None:
    decisions = InMemoryDecisionRepository()
    simulations = InMemorySimulationRepository()

    with pytest.raises(SimulationNotFoundError):
        await GetSimulationUseCase(decisions, simulations).execute(uuid4(), uuid4())
