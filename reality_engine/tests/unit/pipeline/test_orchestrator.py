from __future__ import annotations

import pytest

from reality_engine.ai_gateway.application.gateway import AIGateway
from reality_engine.ai_gateway.domain.ports import ModelTier
from reality_engine.ai_gateway.infrastructure.fake_provider import FakeLLMProvider
from reality_engine.pipeline.domain.schemas import (
    ComprehensionOutput,
    EmotionalLoad,
    EmotionsOutput,
    ExtractedGoal,
    GoalsExtractionOutput,
    GoalSource,
    PsychologicalReadiness,
    PsychologyOutput,
    RecommendedAction,
    RiskAnalysisOutput,
    RiskLevel,
    SafetyGateOutput,
    SummaryOutput,
)
from reality_engine.pipeline.orchestrator import AnalysisPipeline


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
