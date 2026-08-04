"""Agent 3 — Extracción de Objetivos (docs/REALITY_ENGINE.md §2).

Identifies what the user is actually optimizing for, weighting explicit
(user-declared) and inferred goals. Per the spec's documented error case
`weights_do_not_sum_100`: normalization is deterministic post-processing,
not a re-call to the model.
"""

from __future__ import annotations

from reality_engine.ai_gateway.application.gateway import AIGateway
from reality_engine.ai_gateway.domain.ports import ModelTier
from reality_engine.pipeline.agents._prompting import format_context
from reality_engine.pipeline.domain.schemas import ExtractedGoal, GoalsExtractionOutput

_SYSTEM_PROMPT = (
    "A partir del resumen de la decisión y del perfil de objetivos declarado "
    "por el usuario (si existe), identifica hasta 5 objetivos que la persona "
    "está intentando optimizar. Para cada uno, asigna un peso relativo (suma "
    "100) basado en el énfasis del texto y, si existe, el historial de "
    "objetivos previos del usuario. Distingue objetivos explícitos (dichos "
    "directamente) de inferidos. Responde solo JSON según el esquema."
)


def _normalize_weights(goals: list[ExtractedGoal]) -> list[ExtractedGoal]:
    total = sum(goal.weight for goal in goals)
    if total == 0 or total == 100:
        return goals
    return [
        goal.model_copy(update={"weight": round(goal.weight * 100 / total)}) for goal in goals
    ]


class GoalsExtractionAgent:
    def __init__(self, ai_gateway: AIGateway) -> None:
        self._gateway = ai_gateway

    async def run(self, summary: str, declared_goals: list[str]) -> GoalsExtractionOutput:
        result = await self._gateway.generate_structured(
            tier=ModelTier.STRUCTURED_EXTRACTION,
            system_prompt=_SYSTEM_PROMPT,
            user_input=format_context(summary=summary, declared_goals=declared_goals),
            response_model=GoalsExtractionOutput,
        )
        return GoalsExtractionOutput(goals=_normalize_weights(result.goals))
