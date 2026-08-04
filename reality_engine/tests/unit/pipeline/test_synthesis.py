from __future__ import annotations

import pytest

from reality_engine.ai_gateway.application.gateway import AIGateway
from reality_engine.ai_gateway.domain.ports import LLMGenerationError, ModelTier
from reality_engine.ai_gateway.infrastructure.fake_provider import FakeLLMProvider
from reality_engine.pipeline.agents.synthesis import SynthesisAgent
from reality_engine.pipeline.domain.schemas import (
    ComparisonOutput,
    EmotionalLoad,
    EmotionsOutput,
    PsychologicalReadiness,
    PsychologyOutput,
    RankingOutput,
    SynthesisOutput,
)

_RANKING = RankingOutput(ranking=[])
_COMPARISON = ComparisonOutput(comparison_matrix=[])
_PSYCHOLOGY = PsychologyOutput(
    biases_detected=[], psychological_readiness=PsychologicalReadiness.MEDIUM
)
_EMOTIONS = EmotionsOutput(emotions=[], overall_emotional_load=EmotionalLoad.LOW)


@pytest.mark.asyncio
async def test_returns_synthesis_with_reflective_question() -> None:
    expected = SynthesisOutput(
        synthesis="Basado en tus objetivos, el escenario A se alinea más...",
        reflective_question="¿Qué peso le quieres dar a ese miedo?",
    )
    provider = FakeLLMProvider(responses=[expected])
    gateway = AIGateway({ModelTier.REASONING_CREATIVE: [provider]})
    agent = SynthesisAgent(gateway)

    result = await agent.run(_RANKING, _COMPARISON, _PSYCHOLOGY, _EMOTIONS)

    assert result == expected


@pytest.mark.asyncio
async def test_retries_when_imperative_language_detected_then_succeeds() -> None:
    bad = SynthesisOutput(synthesis="Deberías aceptar la oferta.", reflective_question="¿Y bien?")
    good = SynthesisOutput(
        synthesis="Podrías considerar aceptar la oferta.", reflective_question="¿Y bien?"
    )
    provider = FakeLLMProvider(responses=[bad, good])
    gateway = AIGateway({ModelTier.REASONING_CREATIVE: [provider]})
    agent = SynthesisAgent(gateway, max_language_retries=1)

    result = await agent.run(_RANKING, _COMPARISON, _PSYCHOLOGY, _EMOTIONS)

    assert "Deberías" not in result.synthesis
    assert len(provider.calls) == 2


@pytest.mark.asyncio
async def test_raises_when_imperative_language_persists_after_retries() -> None:
    bad = SynthesisOutput(synthesis="Debes terminar la relación.", reflective_question="¿Y bien?")
    provider = FakeLLMProvider(responses=[bad, bad])
    gateway = AIGateway({ModelTier.REASONING_CREATIVE: [provider]})
    agent = SynthesisAgent(gateway, max_language_retries=1)

    with pytest.raises(LLMGenerationError):
        await agent.run(_RANKING, _COMPARISON, _PSYCHOLOGY, _EMOTIONS)
