from __future__ import annotations

import pytest

from reality_engine.ai_gateway.application.gateway import AIGateway
from reality_engine.ai_gateway.domain.ports import ModelTier
from reality_engine.ai_gateway.infrastructure.fake_provider import FakeLLMProvider
from reality_engine.pipeline.agents.learning import LearningAgent
from reality_engine.pipeline.domain.schemas import (
    CalibrationOutput,
    RankedScenario,
    RankingOutput,
    Scenario,
    ScenariosOutput,
)


def _scenarios() -> ScenariosOutput:
    def scenario(scenario_id: str) -> Scenario:
        return Scenario(
            id=scenario_id,
            title="t",
            based_on_option="Aceptar",
            narrative="Podrías crecer.",
            assumptions=[],
            relative_probability=33.3,
            time_horizon_months=12,
        )

    return ScenariosOutput(scenarios=[scenario("a"), scenario("b"), scenario("c")])


@pytest.mark.asyncio
async def test_returns_parsed_calibration_with_matched_scenario() -> None:
    expected = CalibrationOutput(
        closest_scenario_id="a",
        calibration_delta=12.5,
        system_errors_identified=["subestimó el tiempo de adaptación"],
        user_bias_profile_update={"loss_aversion": 0.1},
    )
    provider = FakeLLMProvider(responses=[expected])
    gateway = AIGateway({ModelTier.STRUCTURED_EXTRACTION: [provider]})
    agent = LearningAgent(gateway)

    result = await agent.run(
        reported_outcome="Acepté y me tomó 3 meses adaptarme",
        original_scenarios=_scenarios(),
        original_ranking=RankingOutput(
            ranking=[RankedScenario(scenario_id="a", final_score=70, rank=1)]
        ),
    )

    assert result == expected


@pytest.mark.asyncio
async def test_allows_null_closest_scenario_for_blind_spots() -> None:
    expected = CalibrationOutput(
        closest_scenario_id=None,
        calibration_delta=-30.0,
        system_errors_identified=["ningún escenario anticipó este resultado"],
    )
    provider = FakeLLMProvider(responses=[expected])
    gateway = AIGateway({ModelTier.STRUCTURED_EXTRACTION: [provider]})
    agent = LearningAgent(gateway)

    result = await agent.run(
        reported_outcome="Pasó algo completamente inesperado",
        original_scenarios=_scenarios(),
        original_ranking=RankingOutput(ranking=[]),
    )

    assert result.closest_scenario_id is None
    assert result.system_errors_identified == ["ningún escenario anticipó este resultado"]
