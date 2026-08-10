from __future__ import annotations

import pytest

from reality_engine.ai_gateway.application.gateway import AIGateway
from reality_engine.ai_gateway.domain.ports import ModelTier
from reality_engine.ai_gateway.infrastructure.fake_provider import FakeLLMProvider
from reality_engine.pipeline.agents.emotions import EmotionsAgent
from reality_engine.pipeline.domain.schemas import DetectedEmotion, EmotionalLoad, EmotionsOutput


@pytest.mark.asyncio
async def test_returns_parsed_emotions() -> None:
    expected = EmotionsOutput(
        emotions=[DetectedEmotion(label="ansiedad", intensity=0.7, evidence="ya no puedo dormir")],
        overall_emotional_load=EmotionalLoad.HIGH,
    )
    provider = FakeLLMProvider(responses=[expected])
    gateway = AIGateway({ModelTier.STRUCTURED_EXTRACTION: [provider]})
    agent = EmotionsAgent(gateway)

    result = await agent.run("ya no puedo dormir pensando en esto", "resumen")

    assert result == expected


@pytest.mark.asyncio
async def test_empty_emotions_list_is_valid() -> None:
    expected = EmotionsOutput(emotions=[], overall_emotional_load=EmotionalLoad.LOW)
    provider = FakeLLMProvider(responses=[expected])
    gateway = AIGateway({ModelTier.STRUCTURED_EXTRACTION: [provider]})
    agent = EmotionsAgent(gateway)

    result = await agent.run("texto puramente factual", "resumen")

    assert result.emotions == []
