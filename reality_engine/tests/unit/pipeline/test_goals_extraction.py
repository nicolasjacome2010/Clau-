from __future__ import annotations

import pytest

from reality_engine.ai_gateway.application.gateway import AIGateway
from reality_engine.ai_gateway.domain.ports import ModelTier
from reality_engine.ai_gateway.infrastructure.fake_provider import FakeLLMProvider
from reality_engine.pipeline.agents.goals_extraction import GoalsExtractionAgent
from reality_engine.pipeline.domain.schemas import ExtractedGoal, GoalsExtractionOutput, GoalSource


@pytest.mark.asyncio
async def test_passes_through_weights_that_already_sum_to_100() -> None:
    expected = GoalsExtractionOutput(
        goals=[
            ExtractedGoal(name="Estabilidad", weight=60, source=GoalSource.EXPLICIT),
            ExtractedGoal(name="Crecimiento", weight=40, source=GoalSource.INFERRED),
        ]
    )
    provider = FakeLLMProvider(responses=[expected])
    gateway = AIGateway({ModelTier.STRUCTURED_EXTRACTION: [provider]})
    agent = GoalsExtractionAgent(gateway)

    result = await agent.run("resumen", ["Estabilidad"])

    assert [g.weight for g in result.goals] == [60, 40]


@pytest.mark.asyncio
async def test_normalizes_weights_that_do_not_sum_to_100() -> None:
    raw = GoalsExtractionOutput(
        goals=[
            ExtractedGoal(name="A", weight=30, source=GoalSource.EXPLICIT),
            ExtractedGoal(name="B", weight=30, source=GoalSource.EXPLICIT),
        ]
    )
    provider = FakeLLMProvider(responses=[raw])
    gateway = AIGateway({ModelTier.STRUCTURED_EXTRACTION: [provider]})
    agent = GoalsExtractionAgent(gateway)

    result = await agent.run("resumen", [])

    weights = [g.weight for g in result.goals]
    assert sum(weights) == 100
    assert weights == [50, 50]


@pytest.mark.asyncio
async def test_empty_goal_list_is_left_untouched() -> None:
    provider = FakeLLMProvider(responses=[GoalsExtractionOutput(goals=[])])
    gateway = AIGateway({ModelTier.STRUCTURED_EXTRACTION: [provider]})
    agent = GoalsExtractionAgent(gateway)

    result = await agent.run("resumen", [])

    assert result.goals == []
