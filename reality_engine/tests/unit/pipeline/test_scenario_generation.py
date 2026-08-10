from __future__ import annotations

import pytest

from reality_engine.ai_gateway.application.gateway import AIGateway
from reality_engine.ai_gateway.domain.ports import LLMGenerationError, ModelTier
from reality_engine.ai_gateway.infrastructure.fake_provider import FakeLLMProvider
from reality_engine.pipeline.agents.scenario_generation import ScenarioGenerationAgent
from reality_engine.pipeline.domain.schemas import (
    GoalsExtractionOutput,
    PsychologicalReadiness,
    PsychologyOutput,
    RiskAnalysisOutput,
    Scenario,
    ScenariosOutput,
)

_GOALS = GoalsExtractionOutput(goals=[])
_PSYCHOLOGY = PsychologyOutput(
    biases_detected=[], psychological_readiness=PsychologicalReadiness.MEDIUM
)
_RISKS = RiskAnalysisOutput(risk_map=[])


def _scenario(narrative: str, probability: float) -> Scenario:
    return Scenario(
        id="a",
        title="t",
        based_on_option="Aceptar",
        narrative=narrative,
        assumptions=[],
        relative_probability=probability,
        time_horizon_months=12,
    )


@pytest.mark.asyncio
async def test_returns_scenarios_with_appropriate_conditional_language() -> None:
    output = ScenariosOutput(
        scenarios=[
            _scenario("Podrías sentir mayor estabilidad si aceptas.", 60),
            _scenario("Es plausible que enfrentes más estrés a corto plazo.", 40),
            _scenario("Podrías negociar mejores términos si esperas.", 30),
        ]
    )
    provider = FakeLLMProvider(responses=[output])
    gateway = AIGateway({ModelTier.REASONING_CREATIVE: [provider]})
    agent = ScenarioGenerationAgent(gateway)

    result = await agent.run("resumen", _GOALS, _PSYCHOLOGY, _RISKS)

    assert len(result.scenarios) == 3
    assert len(provider.calls) == 1


@pytest.mark.asyncio
async def test_normalizes_probabilities_that_do_not_sum_to_100() -> None:
    output = ScenariosOutput(
        scenarios=[
            _scenario("Podrías crecer profesionalmente.", 20),
            _scenario("Podrías necesitar más tiempo de adaptación.", 20),
            _scenario("Es plausible que surjan nuevas oportunidades.", 20),
        ]
    )
    provider = FakeLLMProvider(responses=[output])
    gateway = AIGateway({ModelTier.REASONING_CREATIVE: [provider]})
    agent = ScenarioGenerationAgent(gateway)

    result = await agent.run("resumen", _GOALS, _PSYCHOLOGY, _RISKS)

    total = sum(s.relative_probability for s in result.scenarios)
    # Each item is rounded to 2 decimals independently, so the sum can be
    # off by a cent or two (e.g. 33.33 * 3 = 99.99) — that's an accepted
    # characteristic of the normalization, not a bug.
    assert total == pytest.approx(100.0, abs=0.05)


@pytest.mark.asyncio
async def test_retries_once_when_deterministic_language_detected_then_succeeds() -> None:
    bad_output = ScenariosOutput(
        scenarios=[
            _scenario("Serás más feliz si aceptas.", 40),
            _scenario("Podrías sentir alivio.", 30),
            _scenario("Podrías dudar de tu decisión.", 30),
        ]
    )
    good_output = ScenariosOutput(
        scenarios=[
            _scenario("Podrías sentirte más satisfecho si aceptas.", 40),
            _scenario("Podrías sentir alivio.", 30),
            _scenario("Podrías dudar de tu decisión.", 30),
        ]
    )
    provider = FakeLLMProvider(responses=[bad_output, good_output])
    gateway = AIGateway({ModelTier.REASONING_CREATIVE: [provider]})
    agent = ScenarioGenerationAgent(gateway, max_language_retries=1)

    result = await agent.run("resumen", _GOALS, _PSYCHOLOGY, _RISKS)

    assert "Serás" not in result.scenarios[0].narrative
    assert len(provider.calls) == 2


@pytest.mark.asyncio
async def test_raises_when_deterministic_language_persists_after_retries() -> None:
    bad_output = ScenariosOutput(
        scenarios=[
            _scenario("Serás más feliz si aceptas.", 40),
            _scenario("Tendrás más estrés.", 30),
            _scenario("Podrías dudar.", 30),
        ]
    )
    provider = FakeLLMProvider(responses=[bad_output, bad_output])
    gateway = AIGateway({ModelTier.REASONING_CREATIVE: [provider]})
    agent = ScenarioGenerationAgent(gateway, max_language_retries=1)

    with pytest.raises(LLMGenerationError):
        await agent.run("resumen", _GOALS, _PSYCHOLOGY, _RISKS)
