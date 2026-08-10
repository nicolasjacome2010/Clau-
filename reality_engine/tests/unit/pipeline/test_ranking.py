from __future__ import annotations

from reality_engine.pipeline.agents.ranking import RankingAgent
from reality_engine.pipeline.domain.schemas import (
    ComparisonOutput,
    ExtractedGoal,
    GoalAlignmentScore,
    GoalsExtractionOutput,
    GoalSource,
    ScenarioComparison,
)

_GOALS = GoalsExtractionOutput(
    goals=[
        ExtractedGoal(name="Estabilidad", weight=70, source=GoalSource.EXPLICIT),
        ExtractedGoal(name="Crecimiento", weight=30, source=GoalSource.EXPLICIT),
    ]
)


def test_ranks_higher_goal_alignment_above_lower_when_risk_equal() -> None:
    comparison = ComparisonOutput(
        comparison_matrix=[
            ScenarioComparison(
                scenario_id="high-alignment",
                goal_alignment_scores=[
                    GoalAlignmentScore(goal="Estabilidad", score=90, justification="x"),
                    GoalAlignmentScore(goal="Crecimiento", score=90, justification="x"),
                ],
                risk_score=30,
                reversibility_score=50,
            ),
            ScenarioComparison(
                scenario_id="low-alignment",
                goal_alignment_scores=[
                    GoalAlignmentScore(goal="Estabilidad", score=20, justification="x"),
                    GoalAlignmentScore(goal="Crecimiento", score=20, justification="x"),
                ],
                risk_score=30,
                reversibility_score=50,
            ),
        ]
    )

    result = RankingAgent().run(comparison, _GOALS)

    by_id = {r.scenario_id: r for r in result.ranking}
    assert by_id["high-alignment"].rank == 1
    assert by_id["low-alignment"].rank == 2
    assert by_id["high-alignment"].final_score > by_id["low-alignment"].final_score


def test_ties_share_the_same_rank() -> None:
    identical_scores = [
        GoalAlignmentScore(goal="Estabilidad", score=50, justification="x"),
        GoalAlignmentScore(goal="Crecimiento", score=50, justification="x"),
    ]
    comparison = ComparisonOutput(
        comparison_matrix=[
            ScenarioComparison(
                scenario_id="a",
                goal_alignment_scores=identical_scores,
                risk_score=40,
                reversibility_score=40,
            ),
            ScenarioComparison(
                scenario_id="b",
                goal_alignment_scores=identical_scores,
                risk_score=40,
                reversibility_score=40,
            ),
        ]
    )

    result = RankingAgent().run(comparison, _GOALS)

    ranks = {r.scenario_id: r.rank for r in result.ranking}
    assert ranks["a"] == ranks["b"] == 1


def test_unmentioned_goal_contributes_zero_alignment() -> None:
    comparison = ComparisonOutput(
        comparison_matrix=[
            ScenarioComparison(
                scenario_id="only-mentions-one-goal",
                goal_alignment_scores=[
                    GoalAlignmentScore(goal="Estabilidad", score=100, justification="x")
                ],
                risk_score=0,
                reversibility_score=100,
            )
        ]
    )

    result = RankingAgent().run(comparison, _GOALS)

    # weighted_alignment = 100 * 0.7 = 70 (Crecimiento's 30% weight contributes 0)
    # final = 0.7*70 + 0.2*100 + 0.1*100 = 49 + 20 + 10 = 79
    assert result.ranking[0].final_score == 79.0
