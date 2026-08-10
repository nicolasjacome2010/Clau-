"""Agent 1 — Comprensión (docs/REALITY_ENGINE.md §2).

Converts the raw, potentially messy user input into a structured,
neutral representation of the decision, without yet interpreting
emotions or goals.
"""

from __future__ import annotations

from reality_engine.ai_gateway.application.gateway import AIGateway
from reality_engine.ai_gateway.domain.ports import ModelTier
from reality_engine.pipeline.agents._prompting import format_context
from reality_engine.pipeline.domain.schemas import ComprehensionOutput

_SYSTEM_PROMPT = (
    "Extrae de este texto la decisión concreta que la persona está evaluando. "
    "Identifica: la pregunta central, las opciones explícitas mencionadas (si "
    "las hay), el contexto factual relevante (personas, plazos, cifras). No "
    "opines. No completes información que no esté en el texto; si falta "
    "información crítica, indícalo en `missing_info`. Responde solo JSON según "
    "el esquema."
)


class ComprehensionAgent:
    def __init__(self, ai_gateway: AIGateway) -> None:
        self._gateway = ai_gateway

    async def run(self, raw_input: str) -> ComprehensionOutput:
        return await self._gateway.generate_structured(
            tier=ModelTier.STRUCTURED_EXTRACTION,
            system_prompt=_SYSTEM_PROMPT,
            user_input=format_context(raw_input=raw_input),
            response_model=ComprehensionOutput,
        )
