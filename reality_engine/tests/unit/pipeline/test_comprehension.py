from __future__ import annotations

import pytest

from reality_engine.ai_gateway.application.gateway import AIGateway
from reality_engine.ai_gateway.domain.ports import ModelTier
from reality_engine.ai_gateway.infrastructure.fake_provider import FakeLLMProvider
from reality_engine.pipeline.agents.comprehension import ComprehensionAgent
from reality_engine.pipeline.domain.schemas import ComprehensionOutput, FactualContext


@pytest.mark.asyncio
async def test_returns_parsed_comprehension_output() -> None:
    expected = ComprehensionOutput(
        decision_question="¿Debo aceptar la oferta de trabajo en la empresa Z?",
        explicit_options=["Aceptar", "Rechazar"],
        factual_context=FactualContext(entities=["Empresa Z"], deadlines=["2 semanas"]),
        missing_info=[],
        requires_clarification=False,
    )
    provider = FakeLLMProvider(responses=[expected])
    gateway = AIGateway({ModelTier.STRUCTURED_EXTRACTION: [provider]})
    agent = ComprehensionAgent(gateway)

    result = await agent.run("¿Debo aceptar la oferta de trabajo en la empresa Z?")

    assert result == expected
    system_prompt, user_input = provider.calls[0]
    assert "decisión concreta" in system_prompt
    assert "empresa Z" in user_input
