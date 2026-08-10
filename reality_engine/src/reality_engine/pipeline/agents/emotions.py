"""Agent 4 — Extracción de Emociones (docs/REALITY_ENGINE.md §2).

Not diagnostic, not clinical — detects the user's emotional stance toward
the decision to calibrate the tone of the final synthesis and feed the
psychological analysis agent.
"""

from __future__ import annotations

from reality_engine.ai_gateway.application.gateway import AIGateway
from reality_engine.ai_gateway.domain.ports import ModelTier
from reality_engine.pipeline.agents._prompting import format_context
from reality_engine.pipeline.domain.schemas import EmotionsOutput

_SYSTEM_PROMPT = (
    "Identifica las emociones dominantes expresadas o implícitas en el texto "
    "respecto a esta decisión. No hagas diagnóstico clínico. Devuelve "
    "emociones con intensidad relativa (0-1) y evidencia textual breve que "
    "las respalde. Si el texto es puramente factual, devuelve una lista "
    "vacía en vez de forzar una detección. Responde solo JSON según el "
    "esquema."
)


class EmotionsAgent:
    def __init__(self, ai_gateway: AIGateway) -> None:
        self._gateway = ai_gateway

    async def run(self, raw_input: str, summary: str) -> EmotionsOutput:
        return await self._gateway.generate_structured(
            tier=ModelTier.STRUCTURED_EXTRACTION,
            system_prompt=_SYSTEM_PROMPT,
            user_input=format_context(raw_input=raw_input, summary=summary),
            response_model=EmotionsOutput,
        )
