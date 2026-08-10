"""Agent 2 — Resumen (docs/REALITY_ENGINE.md §2).

Produces the canonical, compact summary that every later agent consumes
as shared context, instead of re-sending the full raw input to each of
them (token-cost control per docs/ARCHITECTURE.md §2.3).
"""

from __future__ import annotations

from reality_engine.ai_gateway.application.gateway import AIGateway
from reality_engine.ai_gateway.domain.ports import ModelTier
from reality_engine.pipeline.agents._prompting import format_context
from reality_engine.pipeline.domain.schemas import ComprehensionOutput, SummaryOutput

_SYSTEM_PROMPT = (
    "Resume la siguiente decisión estructurada en un párrafo de máximo 120 "
    "palabras, en tono neutral, apto para ser usado como contexto por otros "
    "sistemas analíticos. No añadas juicios de valor. Responde solo JSON según "
    "el esquema."
)


class SummaryAgent:
    def __init__(self, ai_gateway: AIGateway) -> None:
        self._gateway = ai_gateway

    async def run(self, comprehension: ComprehensionOutput) -> SummaryOutput:
        return await self._gateway.generate_structured(
            tier=ModelTier.STRUCTURED_EXTRACTION,
            system_prompt=_SYSTEM_PROMPT,
            user_input=format_context(
                decision_question=comprehension.decision_question,
                explicit_options=comprehension.explicit_options,
                factual_context=comprehension.factual_context.model_dump(),
            ),
            response_model=SummaryOutput,
        )
