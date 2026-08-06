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
    ListDecisionOutcomesUseCase,
    ListSimulationsForDecisionUseCase,
    ReportDecisionOutcomeInput,
    ReportDecisionOutcomeUseCase,
    RunSimulationInput,
    RunSimulationStreamUseCase,
    RunSimulationUseCase,
)
from core_api.simulations.domain.entities import Simulation, SimulationStageEvent, SimulationStatus
from core_api.simulations.domain.exceptions import (
    DecisionOutcomeAlreadyReportedError,
    NoCompletedSimulationError,
    SimulationNotFoundError,
)
from core_api.simulations.domain.reality_engine_port import (
    RealityEngineCalibrationOutcome,
    RealityEngineError,
    RealityEngineScenario,
    RealityEngineSimulationOutcome,
    RealityEngineStageEvent,
)
from tests.unit.decisions.fakes import InMemoryDecisionRepository
from tests.unit.goals.fakes import InMemoryGoalRepository
from tests.unit.memory.fakes import (
    InMemoryMemoryEmbeddingRepository,
    InMemoryUserBiasProfileRepository,
)
from tests.unit.simulations.fakes import (
    FakeRealityEngineClient,
    InMemoryDecisionOutcomeRepository,
    InMemorySimulationRepository,
)


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
    memories = InMemoryMemoryEmbeddingRepository()
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

    use_case = RunSimulationUseCase(decisions, goals, simulations, reality_engine, memories)
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
async def test_run_simulation_persists_memory_when_reality_engine_returns_one() -> None:
    decisions = InMemoryDecisionRepository()
    goals = InMemoryGoalRepository()
    simulations = InMemorySimulationRepository()
    memories = InMemoryMemoryEmbeddingRepository()
    outcome = _safe_outcome()
    outcome_with_memory = RealityEngineSimulationOutcome(
        safe_to_proceed=outcome.safe_to_proceed,
        safety_gate_result=outcome.safety_gate_result,
        scenarios=outcome.scenarios,
        synthesis_text=outcome.synthesis_text,
        reflective_question=outcome.reflective_question,
        memory_summary="Alejandro está evaluando una oferta de trabajo.",
        memory_embedding=(0.1, 0.2, 0.3),
    )
    reality_engine = FakeRealityEngineClient(responses=[outcome_with_memory])
    user_id = uuid4()
    decision = await _make_draft_decision(decisions, user_id)

    use_case = RunSimulationUseCase(decisions, goals, simulations, reality_engine, memories)
    await use_case.execute(
        RunSimulationInput(decision_id=decision.id, requesting_user_id=user_id)
    )

    stored = await memories.list_for_user(user_id)
    assert len(stored) == 1
    assert stored[0].summary_text == "Alejandro está evaluando una oferta de trabajo."
    assert stored[0].decision_id == decision.id


@pytest.mark.asyncio
async def test_run_simulation_does_not_persist_memory_when_reality_engine_omits_it() -> None:
    decisions = InMemoryDecisionRepository()
    goals = InMemoryGoalRepository()
    simulations = InMemorySimulationRepository()
    memories = InMemoryMemoryEmbeddingRepository()
    reality_engine = FakeRealityEngineClient(responses=[_safe_outcome()])
    user_id = uuid4()
    decision = await _make_draft_decision(decisions, user_id)

    use_case = RunSimulationUseCase(decisions, goals, simulations, reality_engine, memories)
    await use_case.execute(
        RunSimulationInput(decision_id=decision.id, requesting_user_id=user_id)
    )

    assert await memories.list_for_user(user_id) == []


@pytest.mark.asyncio
async def test_run_simulation_unsafe_creates_partial_and_leaves_decision_simulating() -> None:
    decisions = InMemoryDecisionRepository()
    goals = InMemoryGoalRepository()
    simulations = InMemorySimulationRepository()
    memories = InMemoryMemoryEmbeddingRepository()
    reality_engine = FakeRealityEngineClient(responses=[_unsafe_outcome()])
    user_id = uuid4()
    decision = await _make_draft_decision(decisions, user_id)

    use_case = RunSimulationUseCase(decisions, goals, simulations, reality_engine, memories)
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
    memories = InMemoryMemoryEmbeddingRepository()
    reality_engine = FakeRealityEngineClient(responses=[RealityEngineError("network down")])
    user_id = uuid4()
    decision = await _make_draft_decision(decisions, user_id)

    use_case = RunSimulationUseCase(decisions, goals, simulations, reality_engine, memories)
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
    memories = InMemoryMemoryEmbeddingRepository()
    reality_engine = FakeRealityEngineClient()
    owner_id = uuid4()
    decision = await _make_draft_decision(decisions, owner_id)

    use_case = RunSimulationUseCase(decisions, goals, simulations, reality_engine, memories)
    with pytest.raises(DecisionNotFoundError):
        await use_case.execute(
            RunSimulationInput(decision_id=decision.id, requesting_user_id=uuid4())
        )


@pytest.mark.asyncio
async def test_run_simulation_rejects_already_completed_decision() -> None:
    decisions = InMemoryDecisionRepository()
    goals = InMemoryGoalRepository()
    simulations = InMemorySimulationRepository()
    memories = InMemoryMemoryEmbeddingRepository()
    reality_engine = FakeRealityEngineClient()
    user_id = uuid4()
    decision = await _make_draft_decision(decisions, user_id)
    now = datetime.now(UTC)
    archived = decision.with_status(DecisionStatus.CLARIFYING, at=now).with_status(
        DecisionStatus.SIMULATING, at=now
    ).with_status(DecisionStatus.COMPLETED, at=now)
    await decisions.update(archived)

    use_case = RunSimulationUseCase(decisions, goals, simulations, reality_engine, memories)
    with pytest.raises(DecisionInvalidTransition):
        await use_case.execute(
            RunSimulationInput(decision_id=decision.id, requesting_user_id=user_id)
        )


@pytest.mark.asyncio
async def test_run_simulation_stream_yields_stages_before_the_final_simulation() -> None:
    decisions = InMemoryDecisionRepository()
    goals = InMemoryGoalRepository()
    simulations = InMemorySimulationRepository()
    memories = InMemoryMemoryEmbeddingRepository()
    stage_events = [
        RealityEngineStageEvent(stage="safety_gate", status="started"),
        RealityEngineStageEvent(stage="safety_gate", status="completed"),
        RealityEngineStageEvent(stage="comprehension", status="started"),
        RealityEngineStageEvent(stage="comprehension", status="completed"),
    ]
    reality_engine = FakeRealityEngineClient(
        responses=[_safe_outcome()], stream_events=stage_events
    )
    user_id = uuid4()
    decision = await _make_draft_decision(decisions, user_id)

    use_case = RunSimulationStreamUseCase(decisions, goals, simulations, reality_engine, memories)
    events = [
        event
        async for event in use_case.execute(
            RunSimulationInput(decision_id=decision.id, requesting_user_id=user_id)
        )
    ]

    stages = events[:-1]
    final = events[-1]
    assert stages == [
        SimulationStageEvent(stage="safety_gate", status="started"),
        SimulationStageEvent(stage="safety_gate", status="completed"),
        SimulationStageEvent(stage="comprehension", status="started"),
        SimulationStageEvent(stage="comprehension", status="completed"),
    ]
    assert isinstance(final, Simulation)
    assert final.status == SimulationStatus.COMPLETED
    assert reality_engine.stream_calls == [(decision.raw_input, [])]


@pytest.mark.asyncio
async def test_run_simulation_stream_raises_before_any_stage_when_decision_not_owned() -> None:
    decisions = InMemoryDecisionRepository()
    goals = InMemoryGoalRepository()
    simulations = InMemorySimulationRepository()
    memories = InMemoryMemoryEmbeddingRepository()
    reality_engine = FakeRealityEngineClient()
    owner_id = uuid4()
    decision = await _make_draft_decision(decisions, owner_id)

    use_case = RunSimulationStreamUseCase(decisions, goals, simulations, reality_engine, memories)
    events = use_case.execute(
        RunSimulationInput(decision_id=decision.id, requesting_user_id=uuid4())
    )
    with pytest.raises(DecisionNotFoundError):
        await anext(events)
    assert reality_engine.stream_calls == []


@pytest.mark.asyncio
async def test_run_simulation_stream_failure_mid_stream_still_persists_a_failed_simulation() -> (
    None
):
    decisions = InMemoryDecisionRepository()
    goals = InMemoryGoalRepository()
    simulations = InMemorySimulationRepository()
    memories = InMemoryMemoryEmbeddingRepository()

    class _FailingMidStreamClient(FakeRealityEngineClient):
        async def simulate_stream(  # type: ignore[override]
            self, raw_input: str, declared_goals: list[str]
        ) -> object:
            self.stream_calls.append((raw_input, declared_goals))
            yield RealityEngineStageEvent(stage="safety_gate", status="started")
            raise RealityEngineError("connection dropped")

    reality_engine = _FailingMidStreamClient()
    user_id = uuid4()
    decision = await _make_draft_decision(decisions, user_id)

    use_case = RunSimulationStreamUseCase(decisions, goals, simulations, reality_engine, memories)
    events = [
        event
        async for event in use_case.execute(
            RunSimulationInput(decision_id=decision.id, requesting_user_id=user_id)
        )
    ]

    assert events[0] == SimulationStageEvent(stage="safety_gate", status="started")
    final = events[-1]
    assert isinstance(final, Simulation)
    assert final.status == SimulationStatus.FAILED


@pytest.mark.asyncio
async def test_run_simulation_stream_matches_the_unary_use_case_for_the_same_outcome() -> None:
    outcome = _safe_outcome()

    decisions_a = InMemoryDecisionRepository()
    goals_a = InMemoryGoalRepository()
    simulations_a = InMemorySimulationRepository()
    memories_a = InMemoryMemoryEmbeddingRepository()
    user_id = uuid4()
    decision_a = await _make_draft_decision(decisions_a, user_id)
    unary_simulation = await RunSimulationUseCase(
        decisions_a,
        goals_a,
        simulations_a,
        FakeRealityEngineClient(responses=[outcome]),
        memories_a,
    ).execute(RunSimulationInput(decision_id=decision_a.id, requesting_user_id=user_id))

    decisions_b = InMemoryDecisionRepository()
    goals_b = InMemoryGoalRepository()
    simulations_b = InMemorySimulationRepository()
    memories_b = InMemoryMemoryEmbeddingRepository()
    decision_b = await _make_draft_decision(decisions_b, user_id)
    stream_events = [
        event
        async for event in RunSimulationStreamUseCase(
            decisions_b,
            goals_b,
            simulations_b,
            FakeRealityEngineClient(responses=[outcome]),
            memories_b,
        ).execute(RunSimulationInput(decision_id=decision_b.id, requesting_user_id=user_id))
    ]
    streamed_simulation = stream_events[-1]
    assert isinstance(streamed_simulation, Simulation)

    assert streamed_simulation.status == unary_simulation.status
    assert streamed_simulation.synthesis_text == unary_simulation.synthesis_text
    assert len(streamed_simulation.scenarios) == len(unary_simulation.scenarios)


@pytest.mark.asyncio
async def test_list_simulations_for_decision_scoped_to_owner() -> None:
    decisions = InMemoryDecisionRepository()
    goals = InMemoryGoalRepository()
    simulations = InMemorySimulationRepository()
    memories = InMemoryMemoryEmbeddingRepository()
    reality_engine = FakeRealityEngineClient(responses=[_safe_outcome()])
    user_id = uuid4()
    decision = await _make_draft_decision(decisions, user_id)
    await RunSimulationUseCase(decisions, goals, simulations, reality_engine, memories).execute(
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
    memories = InMemoryMemoryEmbeddingRepository()
    reality_engine = FakeRealityEngineClient(responses=[_safe_outcome()])
    user_id = uuid4()
    decision = await _make_draft_decision(decisions, user_id)
    simulation = await RunSimulationUseCase(
        decisions, goals, simulations, reality_engine, memories
    ).execute(RunSimulationInput(decision_id=decision.id, requesting_user_id=user_id))

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


def _calibration_outcome(
    *, closest_scenario_id: str | None = "a"
) -> RealityEngineCalibrationOutcome:
    return RealityEngineCalibrationOutcome(
        closest_scenario_id=closest_scenario_id,
        calibration_delta=15.0,
        system_errors_identified=["overconfidence"],
        user_bias_profile_update={"optimism_bias": 0.7, "out_of_range": 1.4},
    )


async def _completed_simulation_setup() -> tuple[
    InMemoryDecisionRepository,
    InMemorySimulationRepository,
    InMemoryDecisionOutcomeRepository,
    InMemoryUserBiasProfileRepository,
    FakeRealityEngineClient,
    Decision,
    object,
]:
    decisions = InMemoryDecisionRepository()
    goals = InMemoryGoalRepository()
    simulations = InMemorySimulationRepository()
    memories = InMemoryMemoryEmbeddingRepository()
    outcomes = InMemoryDecisionOutcomeRepository()
    profiles = InMemoryUserBiasProfileRepository()
    reality_engine = FakeRealityEngineClient(responses=[_safe_outcome()])
    user_id = uuid4()
    decision = await _make_draft_decision(decisions, user_id)
    await RunSimulationUseCase(decisions, goals, simulations, reality_engine, memories).execute(
        RunSimulationInput(decision_id=decision.id, requesting_user_id=user_id)
    )
    return decisions, simulations, outcomes, profiles, reality_engine, decision, user_id


@pytest.mark.asyncio
async def test_report_decision_outcome_persists_outcome_and_bias_profile() -> None:
    decisions, simulations, outcomes, profiles, _, decision, user_id = (
        await _completed_simulation_setup()
    )
    reality_engine = FakeRealityEngineClient(calibrate_responses=[_calibration_outcome()])

    use_case = ReportDecisionOutcomeUseCase(
        decisions, simulations, outcomes, profiles, reality_engine
    )
    outcome = await use_case.execute(
        ReportDecisionOutcomeInput(
            decision_id=decision.id,
            requesting_user_id=user_id,  # type: ignore[arg-type]
            reported_outcome="Acepté la oferta y me fue bien.",
        )
    )

    assert outcome.calibration_delta == 15.0
    assert outcome.system_errors_identified == ["overconfidence"]
    assert outcome.closest_scenario_id is not None

    stored_profile = await profiles.get_by_user_id(user_id)  # type: ignore[arg-type]
    assert stored_profile is not None
    assert stored_profile.calibration_score == pytest.approx(3.0)  # 0*0.8 + 15*0.2
    bias = next(b for b in stored_profile.biases if b.bias == "optimism_bias")
    assert bias.score == pytest.approx(0.7)
    # `out_of_range` (1.4) must be clamped into a valid [0, 1] confidence.
    out_of_range_bias = next(b for b in stored_profile.biases if b.bias == "out_of_range")
    assert out_of_range_bias.score == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_report_decision_outcome_allows_null_closest_scenario() -> None:
    decisions, simulations, outcomes, profiles, _, decision, user_id = (
        await _completed_simulation_setup()
    )
    reality_engine = FakeRealityEngineClient(
        calibrate_responses=[_calibration_outcome(closest_scenario_id=None)]
    )

    use_case = ReportDecisionOutcomeUseCase(
        decisions, simulations, outcomes, profiles, reality_engine
    )
    outcome = await use_case.execute(
        ReportDecisionOutcomeInput(
            decision_id=decision.id,
            requesting_user_id=user_id,  # type: ignore[arg-type]
            reported_outcome="Pasó algo que no anticipé.",
        )
    )

    assert outcome.closest_scenario_id is None


@pytest.mark.asyncio
async def test_report_decision_outcome_raises_when_decision_not_owned() -> None:
    decisions, simulations, outcomes, profiles, _, decision, _ = (
        await _completed_simulation_setup()
    )
    reality_engine = FakeRealityEngineClient()

    use_case = ReportDecisionOutcomeUseCase(
        decisions, simulations, outcomes, profiles, reality_engine
    )
    with pytest.raises(DecisionNotFoundError):
        await use_case.execute(
            ReportDecisionOutcomeInput(
                decision_id=decision.id,
                requesting_user_id=uuid4(),
                reported_outcome="x",
            )
        )


@pytest.mark.asyncio
async def test_report_decision_outcome_raises_when_no_completed_simulation() -> None:
    decisions = InMemoryDecisionRepository()
    simulations = InMemorySimulationRepository()
    outcomes = InMemoryDecisionOutcomeRepository()
    profiles = InMemoryUserBiasProfileRepository()
    reality_engine = FakeRealityEngineClient()
    user_id = uuid4()
    decision = await _make_draft_decision(decisions, user_id)

    use_case = ReportDecisionOutcomeUseCase(
        decisions, simulations, outcomes, profiles, reality_engine
    )
    with pytest.raises(NoCompletedSimulationError):
        await use_case.execute(
            ReportDecisionOutcomeInput(
                decision_id=decision.id,
                requesting_user_id=user_id,
                reported_outcome="x",
            )
        )


@pytest.mark.asyncio
async def test_report_decision_outcome_rejects_a_second_report() -> None:
    decisions, simulations, outcomes, profiles, _, decision, user_id = (
        await _completed_simulation_setup()
    )
    reality_engine = FakeRealityEngineClient(calibrate_responses=[_calibration_outcome()])

    use_case = ReportDecisionOutcomeUseCase(
        decisions, simulations, outcomes, profiles, reality_engine
    )
    await use_case.execute(
        ReportDecisionOutcomeInput(
            decision_id=decision.id,
            requesting_user_id=user_id,  # type: ignore[arg-type]
            reported_outcome="Acepté la oferta.",
        )
    )
    profile_after_first = await profiles.get_by_user_id(user_id)  # type: ignore[arg-type]
    assert profile_after_first is not None

    with pytest.raises(DecisionOutcomeAlreadyReportedError):
        await use_case.execute(
            ReportDecisionOutcomeInput(
                decision_id=decision.id,
                requesting_user_id=user_id,  # type: ignore[arg-type]
                reported_outcome="Acepté la oferta.",
            )
        )

    # The guard runs before the Reality Engine call, so a rejected duplicate
    # costs neither an LLM round trip nor a second fold into the profile —
    # the whole reason it isn't just a database constraint.
    assert len(reality_engine.calibrate_calls) == 1
    profile_after_second = await profiles.get_by_user_id(user_id)  # type: ignore[arg-type]
    assert profile_after_second is not None
    assert profile_after_second.calibration_score == profile_after_first.calibration_score


@pytest.mark.asyncio
async def test_list_decision_outcomes_returns_only_the_callers_outcomes() -> None:
    decisions, simulations, outcomes, profiles, _, decision, user_id = (
        await _completed_simulation_setup()
    )
    reality_engine = FakeRealityEngineClient(calibrate_responses=[_calibration_outcome()])
    await ReportDecisionOutcomeUseCase(
        decisions, simulations, outcomes, profiles, reality_engine
    ).execute(
        ReportDecisionOutcomeInput(
            decision_id=decision.id,
            requesting_user_id=user_id,  # type: ignore[arg-type]
            reported_outcome="Acepté la oferta.",
        )
    )

    use_case = ListDecisionOutcomesUseCase(decisions, outcomes)

    mine = await use_case.execute(user_id)  # type: ignore[arg-type]
    assert [o.decision_id for o in mine] == [decision.id]

    # Another user's listing must not leak it, even though both rows live in
    # the same table and outcomes carry no user_id of their own.
    assert await use_case.execute(uuid4()) == []


@pytest.mark.asyncio
async def test_list_decision_outcomes_is_empty_before_any_loop_is_closed() -> None:
    decisions = InMemoryDecisionRepository()
    outcomes = InMemoryDecisionOutcomeRepository()
    user_id = uuid4()
    await _make_draft_decision(decisions, user_id)

    assert await ListDecisionOutcomesUseCase(decisions, outcomes).execute(user_id) == []
