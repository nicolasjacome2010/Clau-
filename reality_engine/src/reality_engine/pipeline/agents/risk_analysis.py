"""Agent 6 — Análisis de Riesgos (docs/REALITY_ENGINE.md §2).

The "cold" counterweight to the psychological analysis: objective risks
per option, independent of the user's emotional state.
"""

from __future__ import annotations

from reality_engine.ai_gateway.application.gateway import AIGateway
from reality_engine.ai_gateway.domain.ports import ModelTier
from reality_engine.pipeline.agents._prompting import format_context
from reality_engine.pipeline.domain.schemas import ComprehensionOutput, RiskAnalysisOutput

_SYSTEM_PROMPT = (
    "Para cada opción identificada, lista los riesgos objetivos relevantes "
    "(financiero, temporal, relacional, de reputación, de salud, de "
    "reversibilidad) con una estimación de severidad e irreversibilidad. Sé "
    "concreto y basado en el contexto factual dado, no genérico. Responde "
    "solo JSON según el esquema."
)


class RiskAnalysisAgent:
    def __init__(self, ai_gateway: AIGateway) -> None:
        self._gateway = ai_gateway

    async def run(self, comprehension: ComprehensionOutput) -> RiskAnalysisOutput:
        return await self._gateway.generate_structured(
            tier=ModelTier.STRUCTURED_EXTRACTION,
            system_prompt=_SYSTEM_PROMPT,
            user_input=format_context(
                decision_question=comprehension.decision_question,
                explicit_options=comprehension.explicit_options,
                factual_context=comprehension.factual_context.model_dump(),
            ),
            response_model=RiskAnalysisOutput,
        )
