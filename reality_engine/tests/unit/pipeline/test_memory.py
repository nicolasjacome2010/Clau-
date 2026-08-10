from __future__ import annotations

import pytest

from reality_engine.ai_gateway.application.gateway import AIGateway
from reality_engine.ai_gateway.domain.ports import ModelTier
from reality_engine.ai_gateway.infrastructure.fake_provider import FakeLLMProvider
from reality_engine.pipeline.agents.memory import MemoryAgent
from reality_engine.pipeline.domain.schemas import (
    GoalsExtractionOutput,
    MemoryOutput,
    PsychologicalReadiness,
    PsychologyOutput,
    RankingOutput,
)


@pytest.mark.asyncio
async def test_returns_parsed_memory_output() -> None:
    expected = MemoryOutput(
        memory_summary="Evaluó aceptar una oferta priorizando estabilidad.",
        embedding_ready_text="Decisión sobre oferta laboral, prioriza estabilidad.",
    )
    provider = FakeLLMProvider(responses=[expected])
    gateway = AIGateway({ModelTier.STRUCTURED_EXTRACTION: [provider]})
    agent = MemoryAgent(gateway)

    result = await agent.run(
        summary="resumen",
        goals=GoalsExtractionOutput(goals=[]),
        psychology=PsychologyOutput(
            biases_detected=[], psychological_readiness=PsychologicalReadiness.MEDIUM
        ),
        ranking=RankingOutput(ranking=[]),
    )

    assert result == expected
