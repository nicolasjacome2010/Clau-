from __future__ import annotations

import pytest

from reality_engine.ai_gateway.application.gateway import AIGateway
from reality_engine.ai_gateway.domain.ports import ModelTier
from reality_engine.ai_gateway.infrastructure.fake_embedding_provider import FakeEmbeddingProvider
from reality_engine.ai_gateway.infrastructure.fake_provider import FakeLLMProvider
from reality_engine.pipeline.domain.events import (
    HaltedEvent,
    PipelineEvent,
    PipelineStage,
    StageEvent,
)
from reality_engine.pipeline.domain.schemas import (
    ComparisonOutput,
    ComprehensionOutput,
    EmotionalLoad,
    EmotionsOutput,
    ExtractedGoal,
    GoalAlignmentScore,
    GoalsExtractionOutput,
    GoalSource,
    MemoryOutput,
    PsychologicalReadiness,
    PsychologyOutput,
    RecommendedAction,
    RiskAnalysisOutput,
    RiskLevel,
    SafetyGateOutput,
    Scenario,
    ScenarioComparison,
    ScenariosOutput,
    SummaryOutput,
    SynthesisOutput,
)
from reality_engine.pipeline.orchestrator import AnalysisPipeline, SimulationPipeline


def _safe_gateway() -> tuple[AIGateway, FakeLLMProvider, FakeLLMProvider]:
    safety_provider = FakeLLMProvider(
        responses=[
            SafetyGateOutput(
                risk_level=RiskLevel.NONE,
                signals_detected=[],
                safe_to_proceed=True,
                recommended_action=RecommendedAction.PROCEED,
            )
        ]
    )
    extraction_provider = FakeLLMProvider(
        responses=[
            ComprehensionOutput(
                decision_question="¿Debo aceptar?",
                explicit_options=["Sí", "No"],
                requires_clarification=False,
            ),
            SummaryOutput(summary="resumen"),
            GoalsExtractionOutput(
                goals=[ExtractedGoal(name="Estabilidad", weight=100, source=GoalSource.EXPLICIT)]
            ),
            EmotionsOutput(emotions=[], overall_emotional_load=EmotionalLoad.LOW),
            PsychologyOutput(
                biases_detected=[], psychological_readiness=PsychologicalReadiness.HIGH
            ),
            RiskAnalysisOutput(risk_map=[]),
        ]
    )
    gateway = AIGateway(
        {
            ModelTier.SAFETY_CLASSIFICATION: [safety_provider],
            ModelTier.STRUCTURED_EXTRACTION: [extraction_provider],
        }
    )
    return gateway, safety_provider, extraction_provider


@pytest.mark.asyncio
async def test_full_pipeline_runs_all_agents_when_safe() -> None:
    gateway, safety_provider, extraction_provider = _safe_gateway()
    pipeline = AnalysisPipeline(gateway)

    result = await pipeline.run("¿Debo aceptar la oferta?", declared_goals=["Estabilidad"])

    assert result.safety.safe_to_proceed is True
    assert result.comprehension is not None
    assert result.summary is not None
    assert result.goals is not None
    assert result.emotions is not None
    assert result.psychology is not None
    assert result.risks is not None
    assert len(safety_provider.calls) == 1
    assert len(extraction_provider.calls) == 6


@pytest.mark.asyncio
async def test_pipeline_short_circuits_when_unsafe() -> None:
    safety_provider = FakeLLMProvider(
        responses=[
            SafetyGateOutput(
                risk_level=RiskLevel.ACUTE_RISK,
                signals_detected=["pattern"],
                safe_to_proceed=False,
                recommended_action=RecommendedAction.HALT_AND_REFER,
            )
        ]
    )
    extraction_provider = FakeLLMProvider()  # no canned responses: must never be called
    gateway = AIGateway(
        {
            ModelTier.SAFETY_CLASSIFICATION: [safety_provider],
            ModelTier.STRUCTURED_EXTRACTION: [extraction_provider],
        }
    )
    pipeline = AnalysisPipeline(gateway)

    result = await pipeline.run("contenido de alto riesgo")

    assert result.safety.safe_to_proceed is False
    assert result.comprehension is None
    assert result.summary is None
    assert extraction_provider.calls == []


def _scenario(scenario_id: str, probability: float) -> Scenario:
    return Scenario(
        id=scenario_id,
        title="t",
        based_on_option="Aceptar",
        narrative="Podrías sentir mayor estabilidad.",
        assumptions=[],
        relative_probability=probability,
        time_horizon_months=12,
    )


def _full_safe_gateway(
    *, embedding_provider: FakeEmbeddingProvider | None = None
) -> tuple[AIGateway, FakeLLMProvider, FakeLLMProvider, FakeLLMProvider]:
    """Same as `_safe_gateway`, but with Agent 8's (Comparación) and Agent
    11's (Memoria) responses appended to the extraction tier, and a
    reasoning-creative tier wired up for Agents 7 (Generación de
    Escenarios) and 10 (Síntesis).
    """
    safety_provider = FakeLLMProvider(
        responses=[
            SafetyGateOutput(
                risk_level=RiskLevel.NONE,
                signals_detected=[],
                safe_to_proceed=True,
                recommended_action=RecommendedAction.PROCEED,
            )
        ]
    )
    extraction_provider = FakeLLMProvider(
        responses=[
            ComprehensionOutput(
                decision_question="¿Debo aceptar?",
                explicit_options=["Sí", "No"],
                requires_clarification=False,
            ),
            SummaryOutput(summary="resumen"),
            GoalsExtractionOutput(
                goals=[ExtractedGoal(name="Estabilidad", weight=100, source=GoalSource.EXPLICIT)]
            ),
            EmotionsOutput(emotions=[], overall_emotional_load=EmotionalLoad.LOW),
            PsychologyOutput(
                biases_detected=[], psychological_readiness=PsychologicalReadiness.HIGH
            ),
            RiskAnalysisOutput(risk_map=[]),
            ComparisonOutput(
                comparison_matrix=[
                    ScenarioComparison(
                        scenario_id="a",
                        goal_alignment_scores=[
                            GoalAlignmentScore(goal="Estabilidad", score=80, justification="x")
                        ],
                        risk_score=20,
                        reversibility_score=60,
                    )
                ]
            ),
            MemoryOutput(
                memory_summary="Evaluó aceptar una oferta priorizando estabilidad.",
                embedding_ready_text="oferta laboral, estabilidad",
            ),
        ]
    )
    reasoning_provider = FakeLLMProvider(
        responses=[
            ScenariosOutput(
                scenarios=[_scenario("a", 40), _scenario("b", 30), _scenario("c", 30)]
            ),
            SynthesisOutput(synthesis="Podrías...", reflective_question="¿Qué piensas?"),
        ]
    )
    gateway = AIGateway(
        {
            ModelTier.SAFETY_CLASSIFICATION: [safety_provider],
            ModelTier.STRUCTURED_EXTRACTION: [extraction_provider],
            ModelTier.REASONING_CREATIVE: [reasoning_provider],
        },
        embedding_providers=[embedding_provider] if embedding_provider else None,
    )
    return gateway, safety_provider, extraction_provider, reasoning_provider


@pytest.mark.asyncio
async def test_simulation_pipeline_runs_agents_7_to_11_when_safe() -> None:
    embedding_provider = FakeEmbeddingProvider(responses=[[0.1, 0.2, 0.3]])
    gateway, safety_provider, extraction_provider, reasoning_provider = _full_safe_gateway(
        embedding_provider=embedding_provider
    )
    pipeline = SimulationPipeline(gateway)

    result = await pipeline.run("¿Debo aceptar la oferta?", declared_goals=["Estabilidad"])

    assert result.analysis.safety.safe_to_proceed is True
    assert result.scenarios is not None
    assert result.comparison is not None
    assert result.ranking is not None
    assert result.synthesis is not None
    assert result.memory is not None
    assert result.memory.embedding == [0.1, 0.2, 0.3]
    assert len(safety_provider.calls) == 1
    assert len(extraction_provider.calls) == 8  # 6 analysis agents + Comparación + Memoria
    assert len(reasoning_provider.calls) == 2  # Escenarios + Síntesis


@pytest.mark.asyncio
async def test_simulation_pipeline_memory_failure_does_not_fail_simulation() -> None:
    """No embedding provider configured — Agent 11's LLM call still
    succeeds, but `AIGateway.embed()` has nothing to call, so `memory`
    stays None while the rest of the result is unaffected.
    """
    gateway, *_ = _full_safe_gateway(embedding_provider=None)
    pipeline = SimulationPipeline(gateway)

    result = await pipeline.run("¿Debo aceptar la oferta?", declared_goals=["Estabilidad"])

    assert result.synthesis is not None
    assert result.memory is None


@pytest.mark.asyncio
async def test_simulation_pipeline_short_circuits_when_unsafe() -> None:
    safety_provider = FakeLLMProvider(
        responses=[
            SafetyGateOutput(
                risk_level=RiskLevel.ACUTE_RISK,
                signals_detected=["pattern"],
                safe_to_proceed=False,
                recommended_action=RecommendedAction.HALT_AND_REFER,
            )
        ]
    )
    extraction_provider = FakeLLMProvider()
    reasoning_provider = FakeLLMProvider()  # must never be called
    gateway = AIGateway(
        {
            ModelTier.SAFETY_CLASSIFICATION: [safety_provider],
            ModelTier.STRUCTURED_EXTRACTION: [extraction_provider],
            ModelTier.REASONING_CREATIVE: [reasoning_provider],
        }
    )
    pipeline = SimulationPipeline(gateway)

    result = await pipeline.run("contenido de alto riesgo")

    assert result.analysis.safety.safe_to_proceed is False
    assert result.scenarios is None
    assert result.synthesis is None
    assert result.memory is None
    assert reasoning_provider.calls == []


@pytest.mark.asyncio
async def test_pipeline_reports_every_stage_in_order() -> None:
    embedding_provider = FakeEmbeddingProvider(responses=[[0.1, 0.2, 0.3]])
    gateway, *_ = _full_safe_gateway(embedding_provider=embedding_provider)
    pipeline = SimulationPipeline(gateway)
    events: list[PipelineEvent] = []

    async def listen(event: PipelineEvent) -> None:
        events.append(event)

    await pipeline.run("¿Debo aceptar?", declared_goals=["Estabilidad"], on_stage=listen)

    stages = [e.stage for e in events if isinstance(e, StageEvent)]
    assert stages == [
        stage
        for stage in (
            PipelineStage.SAFETY_GATE,
            PipelineStage.COMPREHENSION,
            PipelineStage.SUMMARY,
            PipelineStage.GOALS_EXTRACTION,
            PipelineStage.EMOTIONS,
            PipelineStage.PSYCHOLOGY,
            PipelineStage.RISK_ANALYSIS,
            PipelineStage.SCENARIO_GENERATION,
            PipelineStage.COMPARISON,
            PipelineStage.RANKING,
            PipelineStage.SYNTHESIS,
            PipelineStage.MEMORY,
        )
        for _ in range(2)  # started, then completed
    ]
    # Every stage is bracketed: a client needs the "started" edge to have
    # anything to show as in progress.
    assert [e.status for e in events if isinstance(e, StageEvent)] == [
        "started" if index % 2 == 0 else "completed" for index in range(24)
    ]


@pytest.mark.asyncio
async def test_an_unwatched_run_behaves_identically() -> None:
    """The listener is optional, and the pipeline must not depend on it."""
    embedding_provider = FakeEmbeddingProvider(responses=[[0.1, 0.2, 0.3]])
    gateway, *_ = _full_safe_gateway(embedding_provider=embedding_provider)

    result = await SimulationPipeline(gateway).run("¿Debo aceptar?", declared_goals=[])

    assert result.synthesis is not None


@pytest.mark.asyncio
async def test_a_halt_is_reported_as_its_own_event() -> None:
    # Not as "one more completed stage": the run ends here, and a listener
    # that missed that would wait forever for scenarios.
    safety_provider = FakeLLMProvider(
        responses=[
            SafetyGateOutput(
                risk_level=RiskLevel.ACUTE_RISK,
                signals_detected=["pattern"],
                safe_to_proceed=False,
                recommended_action=RecommendedAction.HALT_AND_REFER,
            )
        ]
    )
    gateway = AIGateway({ModelTier.SAFETY_CLASSIFICATION: [safety_provider]})
    events: list[PipelineEvent] = []

    async def listen(event: PipelineEvent) -> None:
        events.append(event)

    await SimulationPipeline(gateway).run("...", on_stage=listen)

    assert isinstance(events[-1], HaltedEvent)
    assert [e.stage for e in events if isinstance(e, StageEvent)] == [
        PipelineStage.SAFETY_GATE,
        PipelineStage.SAFETY_GATE,
    ]


@pytest.mark.asyncio
async def test_memory_failure_still_completes_its_stage() -> None:
    # Memory is an enhancement; surfacing its failure as an unfinished
    # stage would make a successful simulation look broken.
    gateway, *_ = _full_safe_gateway(embedding_provider=None)
    events: list[PipelineEvent] = []

    async def listen(event: PipelineEvent) -> None:
        events.append(event)

    result = await SimulationPipeline(gateway).run("¿Y?", on_stage=listen)

    assert result.memory is None
    memory_events = [
        e for e in events if isinstance(e, StageEvent) and e.stage is PipelineStage.MEMORY
    ]
    assert [e.status for e in memory_events] == ["started", "completed"]
