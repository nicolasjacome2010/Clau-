"""Agent 11 — Memoria (docs/REALITY_ENGINE.md §2).

Produces a compact summary optimized for future semantic retrieval by the
same user. The embedding vector itself is computed by the orchestrator via
`AIGateway.embed()` right after this agent runs — kept out of this class
so it stays a single LLM call, the same shape as every other agent.
"""

from __future__ import annotations

from reality_engine.ai_gateway.application.gateway import AIGateway
from reality_engine.ai_gateway.domain.ports import ModelTier
from reality_engine.pipeline.agents._prompting import format_context
from reality_engine.pipeline.domain.schemas import (
    GoalsExtractionOutput,
    MemoryOutput,
    PsychologyOutput,
    RankingOutput,
)

_SYSTEM_PROMPT = (
    "Genera un resumen de máximo 60 palabras de esta decisión y su resultado "
    "de simulación, optimizado para ser recuperado semánticamente en el "
    "futuro como contexto de decisiones similares de la misma persona. "
    "Responde solo JSON según el esquema."
)


class MemoryAgent:
    def __init__(self, ai_gateway: AIGateway) -> None:
        self._gateway = ai_gateway

    async def run(
        self,
        summary: str,
        goals: GoalsExtractionOutput,
        psychology: PsychologyOutput,
        ranking: RankingOutput,
    ) -> MemoryOutput:
        return await self._gateway.generate_structured(
            tier=ModelTier.STRUCTURED_EXTRACTION,
            system_prompt=_SYSTEM_PROMPT,
            user_input=format_context(
                summary=summary,
                goals=goals.model_dump(),
                biases_detected=psychology.model_dump()["biases_detected"],
                ranking=ranking.model_dump(),
            ),
            response_model=MemoryOutput,
        )
