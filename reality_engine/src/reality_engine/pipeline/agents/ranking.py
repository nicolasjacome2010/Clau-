"""Agent 9 — Ranking (docs/REALITY_ENGINE.md §2).

Not an LLM call. The final ranking is computed by a deterministic formula
over Agent 8's comparison matrix, never asked of a generative model — this
guarantees the ranking is reproducible and auditable (docs/PRD.md §2,
"trazabilidad total").

v1 scoring formula (documented, tunable — not a validated decision-science
result): 70% weighted goal alignment, 20% inverse risk, 10% reversibility.
Ties share the same rank (docs/REALITY_ENGINE.md §2, error
`tie_between_scenarios`: shown as tied in the UI rather than artificially
broken).
"""

from __future__ import annotations

from reality_engine.pipeline.domain.schemas import (
    ComparisonOutput,
    GoalsExtractionOutput,
    RankedScenario,
    RankingOutput,
    ScenarioComparison,
)

_GOAL_ALIGNMENT_WEIGHT = 0.7
_RISK_WEIGHT = 0.2
_REVERSIBILITY_WEIGHT = 0.1


def _final_score(comparison_row: ScenarioComparison, weight_by_goal_name: dict[str, int]) -> float:
    weighted_alignment = sum(
        item.score * weight_by_goal_name.get(item.goal, 0) / 100
        for item in comparison_row.goal_alignment_scores
    )
    return round(
        _GOAL_ALIGNMENT_WEIGHT * weighted_alignment
        + _RISK_WEIGHT * (100 - comparison_row.risk_score)
        + _REVERSIBILITY_WEIGHT * comparison_row.reversibility_score,
        2,
    )


class RankingAgent:
    def run(self, comparison: ComparisonOutput, goals: GoalsExtractionOutput) -> RankingOutput:
        weight_by_goal_name = {goal.name: goal.weight for goal in goals.goals}

        scored = [
            (row.scenario_id, _final_score(row, weight_by_goal_name))
            for row in comparison.comparison_matrix
        ]
        scored.sort(key=lambda pair: pair[1], reverse=True)

        ranking: list[RankedScenario] = []
        rank = 0
        last_score: float | None = None
        for scenario_id, score in scored:
            if score != last_score:
                rank += 1
                last_score = score
            ranking.append(RankedScenario(scenario_id=scenario_id, final_score=score, rank=rank))

        return RankingOutput(ranking=ranking)
