from __future__ import annotations

import pytest

from reality_engine.ai_gateway.application.gateway import AIGateway
from reality_engine.ai_gateway.domain.ports import ModelTier
from reality_engine.ai_gateway.infrastructure.fake_provider import FakeLLMProvider
from reality_engine.pipeline.agents.summary import SummaryAgent
from reality_engine.pipeline.domain.schemas import ComprehensionOutput, SummaryOutput


@pytest.mark.asyncio
async def test_returns_parsed_summary() -> None:
    expected = SummaryOutput(summary="Resumen neutral de la decisión.")
    provider = FakeLLMProvider(responses=[expected])
    gateway = AIGateway({ModelTier.STRUCTURED_EXTRACTION: [provider]})
    agent = SummaryAgent(gateway)
    comprehension = ComprehensionOutput(
        decision_question="¿Debo mudarme?",
        explicit_options=["Sí", "No"],
        requires_clarification=False,
    )

    result = await agent.run(comprehension)

    assert result == expected
    _, user_input = provider.calls[0]
    assert "¿Debo mudarme?" in user_input
