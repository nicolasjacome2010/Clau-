from __future__ import annotations

import pytest

from reality_engine.ai_gateway.application.gateway import AIGateway
from reality_engine.ai_gateway.domain.ports import ModelTier
from reality_engine.ai_gateway.infrastructure.fake_provider import FakeLLMProvider
from reality_engine.pipeline.domain.schemas import (
    ComparisonOutput,
    ComprehensionOutput,
    EmotionalLoad,
    EmotionsOutput,
    ExtractedGoal,
    GoalAlignmentScore,
    GoalsExtractionOutput,
    GoalSource,
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


def _full_safe_gateway() -> tuple[AIGateway, FakeLLMProvider, FakeLLMProvider, FakeLLMProvider]:
    """Same as `_safe_gateway`, but with Agent 8's (Comparación) response
    appended to the extraction tier and a reasoning-creative tier wired up
    for Agents 7 (Generación de Escenarios) and 10 (Síntesis).
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
        }
    )
    return gateway, safety_provider, extraction_provider, reasoning_provider


@pytest.mark.asyncio
async def test_simulation_pipeline_runs_agents_7_to_10_when_safe() -> None:
    gateway, safety_provider, extraction_provider, reasoning_provider = _full_safe_gateway()
    pipeline = SimulationPipeline(gateway)

    result = await pipeline.run("¿Debo aceptar la oferta?", declared_goals=["Estabilidad"])

    assert result.analysis.safety.safe_to_proceed is True
    assert result.scenarios is not None
    assert result.comparison is not None
    assert result.ranking is not None
    assert result.synthesis is not None
    assert len(safety_provider.calls) == 1
    assert len(extraction_provider.calls) == 7  # 6 analysis agents + Comparación
    assert len(reasoning_provider.calls) == 2  # Escenarios + Síntesis


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
    assert reasoning_provider.calls == []
