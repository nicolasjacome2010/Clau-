"""Agent 10 — Síntesis (docs/REALITY_ENGINE.md §2).

Translates the ranking and comparison matrix into the human explanation
most users will actually read — warm but rigorous, mentions relevant
biases with tact, and closes with a reflective question, never an order
(docs/PRD.md §2.3, "el usuario decide").
"""

from __future__ import annotations

from reality_engine.ai_gateway.application.gateway import AIGateway
from reality_engine.ai_gateway.domain.ports import LLMGenerationError, ModelTier
from reality_engine.pipeline.agents._language_guards import find_imperative_language
from reality_engine.pipeline.agents._prompting import format_context
from reality_engine.pipeline.domain.schemas import (
    ComparisonOutput,
    EmotionsOutput,
    PsychologyOutput,
    RankingOutput,
    SynthesisOutput,
)

_SYSTEM_PROMPT = (
    "Escribe una síntesis en segunda persona, cálida pero rigurosa, de "
    "máximo 250 palabras, que explique por qué el escenario mejor rankeado "
    "se alinea más con los objetivos declarados, mencione con tacto (no "
    "acusatoriamente) algún sesgo relevante detectado, y termine con una "
    "pregunta abierta que invite a la reflexión, no con una orden "
    "('deberías'). Nunca uses lenguaje de certeza sobre el futuro. Responde "
    "solo JSON según el esquema."
)


class SynthesisAgent:
    def __init__(self, ai_gateway: AIGateway, *, max_language_retries: int = 1) -> None:
        self._gateway = ai_gateway
        self._max_language_retries = max_language_retries

    async def run(
        self,
        ranking: RankingOutput,
        comparison: ComparisonOutput,
        psychology: PsychologyOutput,
        emotions: EmotionsOutput,
    ) -> SynthesisOutput:
        user_input = format_context(
            ranking=ranking.model_dump(),
            comparison=comparison.model_dump(),
            biases_detected=psychology.model_dump()["biases_detected"],
            emotions=emotions.model_dump(),
        )

        for _attempt in range(self._max_language_retries + 1):
            result = await self._gateway.generate_structured(
                tier=ModelTier.REASONING_CREATIVE,
                system_prompt=_SYSTEM_PROMPT,
                user_input=user_input,
                response_model=SynthesisOutput,
            )
            if not find_imperative_language(result.synthesis):
                return result

        raise LLMGenerationError("Synthesis kept using imperative language after retries")
