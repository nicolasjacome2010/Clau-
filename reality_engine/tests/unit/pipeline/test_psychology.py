from __future__ import annotations

import pytest

from reality_engine.ai_gateway.application.gateway import AIGateway
from reality_engine.ai_gateway.domain.ports import ModelTier
from reality_engine.ai_gateway.infrastructure.fake_provider import FakeLLMProvider
from reality_engine.pipeline.agents.psychology import PsychologyAgent
from reality_engine.pipeline.domain.schemas import (
    DetectedBias,
    EmotionalLoad,
    EmotionsOutput,
    PsychologicalReadiness,
    PsychologyOutput,
)


@pytest.mark.asyncio
async def test_returns_parsed_psychology_output_without_bias_profile() -> None:
    expected = PsychologyOutput(
        biases_detected=[
            DetectedBias(
                bias="loss_aversion", manifestation="teme perder estabilidad", confidence=0.8
            )
        ],
        psychological_readiness=PsychologicalReadiness.MEDIUM,
    )
    provider = FakeLLMProvider(responses=[expected])
    gateway = AIGateway({ModelTier.STRUCTURED_EXTRACTION: [provider]})
    agent = PsychologyAgent(gateway)
    emotions = EmotionsOutput(emotions=[], overall_emotional_load=EmotionalLoad.MEDIUM)

    result = await agent.run("resumen", emotions)

    assert result == expected
    _, user_input = provider.calls[0]
    assert '"user_bias_profile": {}' in user_input


@pytest.mark.asyncio
async def test_passes_through_bias_profile_when_provided() -> None:
    expected = PsychologyOutput(
        biases_detected=[], psychological_readiness=PsychologicalReadiness.HIGH
    )
    provider = FakeLLMProvider(responses=[expected])
    gateway = AIGateway({ModelTier.STRUCTURED_EXTRACTION: [provider]})
    agent = PsychologyAgent(gateway)
    emotions = EmotionsOutput(emotions=[], overall_emotional_load=EmotionalLoad.LOW)

    await agent.run("resumen", emotions, user_bias_profile={"loss_aversion": 0.6})

    _, user_input = provider.calls[0]
    assert "loss_aversion" in user_input
