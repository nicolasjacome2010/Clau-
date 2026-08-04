"""Agent 8 — Comparación (docs/REALITY_ENGINE.md §2).

Scores each scenario against the user's weighted goals and the risk map,
producing the explicit, auditable matrix that Agent 9 (Ranking) will
aggregate deterministically.
"""

from __future__ import annotations

from reality_engine.ai_gateway.application.gateway import AIGateway
from reality_engine.ai_gateway.domain.ports import ModelTier
from reality_engine.pipeline.agents._prompting import format_context
from reality_engine.pipeline.domain.schemas import (
    ComparisonOutput,
    GoalsExtractionOutput,
    RiskAnalysisOutput,
    ScenariosOutput,
)

_SYSTEM_PROMPT = (
    "Para cada escenario, evalúa qué tan bien satisface cada objetivo "
    "ponderado del usuario (0-100) y asigna un score de riesgo y de "
    "reversibilidad. Justifica cada score en una frase. Sé consistente: si "
    "dos escenarios comparten un supuesto, su score en el criterio afectado "
    "debe ser coherente entre sí. Responde solo JSON según el esquema."
)


class ComparisonAgent:
    def __init__(self, ai_gateway: AIGateway) -> None:
        self._gateway = ai_gateway

    async def run(
        self,
        scenarios: ScenariosOutput,
        goals: GoalsExtractionOutput,
        risks: RiskAnalysisOutput,
    ) -> ComparisonOutput:
        return await self._gateway.generate_structured(
            tier=ModelTier.STRUCTURED_EXTRACTION,
            system_prompt=_SYSTEM_PROMPT,
            user_input=format_context(
                scenarios=scenarios.model_dump(),
                goals=goals.model_dump(),
                risks=risks.model_dump(),
            ),
            response_model=ComparisonOutput,
        )
