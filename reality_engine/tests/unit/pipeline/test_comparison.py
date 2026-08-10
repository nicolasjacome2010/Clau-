from __future__ import annotations

import pytest

from reality_engine.ai_gateway.application.gateway import AIGateway
from reality_engine.ai_gateway.domain.ports import ModelTier
from reality_engine.ai_gateway.infrastructure.fake_provider import FakeLLMProvider
from reality_engine.pipeline.agents.comparison import ComparisonAgent
from reality_engine.pipeline.domain.schemas import (
    ComparisonOutput,
    GoalAlignmentScore,
    GoalsExtractionOutput,
    RiskAnalysisOutput,
    Scenario,
    ScenarioComparison,
    ScenariosOutput,
)


@pytest.mark.asyncio
async def test_returns_parsed_comparison_matrix() -> None:
    expected = ComparisonOutput(
        comparison_matrix=[
            ScenarioComparison(
                scenario_id="a",
                goal_alignment_scores=[
                    GoalAlignmentScore(
                        goal="Estabilidad", score=80, justification="alta alineación"
                    )
                ],
                risk_score=30,
                reversibility_score=60,
            )
        ]
    )
    provider = FakeLLMProvider(responses=[expected])
    gateway = AIGateway({ModelTier.STRUCTURED_EXTRACTION: [provider]})
    agent = ComparisonAgent(gateway)

    def _scenario(scenario_id: str, probability: float) -> Scenario:
        return Scenario(
            id=scenario_id,
            title="t",
            based_on_option="Aceptar",
            narrative="Podrías crecer profesionalmente.",
            assumptions=[],
            relative_probability=probability,
            time_horizon_months=12,
        )

    scenarios = ScenariosOutput(
        scenarios=[_scenario("a", 50), _scenario("b", 30), _scenario("c", 20)]
    )

    result = await agent.run(
        scenarios, GoalsExtractionOutput(goals=[]), RiskAnalysisOutput(risk_map=[])
    )

    assert result == expected
