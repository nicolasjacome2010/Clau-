from __future__ import annotations

import pytest

from reality_engine.ai_gateway.application.gateway import AIGateway
from reality_engine.ai_gateway.domain.ports import LLMGenerationError, ModelTier
from reality_engine.ai_gateway.infrastructure.fake_provider import FakeLLMProvider
from reality_engine.pipeline.agents.safety_gate import SafetyGateAgent
from reality_engine.pipeline.domain.schemas import RecommendedAction, RiskLevel, SafetyGateOutput


@pytest.mark.asyncio
async def test_deterministic_prescreen_halts_without_calling_the_model() -> None:
    provider = FakeLLMProvider()  # no canned responses: would raise if ever called
    gateway = AIGateway({ModelTier.SAFETY_CLASSIFICATION: [provider]})
    agent = SafetyGateAgent(gateway)

    result = await agent.run("Ya no puedo más, quiero quitarme la vida")

    assert result.risk_level == RiskLevel.ACUTE_RISK
    assert result.safe_to_proceed is False
    assert result.recommended_action == RecommendedAction.HALT_AND_REFER
    assert provider.calls == []  # deterministic path never touched the LLM


@pytest.mark.asyncio
async def test_defers_to_llm_classifier_when_no_pattern_matches() -> None:
    expected = SafetyGateOutput(
        risk_level=RiskLevel.NONE,
        signals_detected=[],
        safe_to_proceed=True,
        recommended_action=RecommendedAction.PROCEED,
    )
    provider = FakeLLMProvider(responses=[expected])
    gateway = AIGateway({ModelTier.SAFETY_CLASSIFICATION: [provider]})
    agent = SafetyGateAgent(gateway)

    result = await agent.run("¿Debo aceptar la oferta de trabajo en la empresa Z?")

    assert result == expected
    assert len(provider.calls) == 1


@pytest.mark.asyncio
async def test_fails_safe_to_halt_when_classifier_is_unavailable() -> None:
    provider = FakeLLMProvider(responses=[LLMGenerationError("provider down")])
    gateway = AIGateway({ModelTier.SAFETY_CLASSIFICATION: [provider]}, retries_per_provider=0)
    agent = SafetyGateAgent(gateway)

    result = await agent.run("¿Debo mudarme a otra ciudad?")

    assert result.risk_level == RiskLevel.ACUTE_RISK
    assert result.safe_to_proceed is False
    assert result.recommended_action == RecommendedAction.HALT_AND_REFER
    assert "classification_failed" in result.signals_detected


@pytest.mark.asyncio
async def test_fails_safe_when_no_provider_is_configured_at_all() -> None:
    """Matches config.py's documented behavior: an unconfigured deployment
    (no OPENAI_API_KEY) must never silently let unscreened input through.
    """
    gateway = AIGateway({})
    agent = SafetyGateAgent(gateway)

    result = await agent.run("¿Debo cambiar de carrera?")

    assert result.risk_level == RiskLevel.ACUTE_RISK
    assert result.recommended_action == RecommendedAction.HALT_AND_REFER
