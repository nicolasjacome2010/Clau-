"""Agent 5 — Análisis Psicológico (docs/REALITY_ENGINE.md §2).

Identifies cognitive biases in play. `user_bias_profile` from the spec
(the user's historical bias profile, owned by Core API's `identity`/
`memory` slice — not yet built, see docs/DATABASE.md §2.10) is an optional
input here: this service has no persistence of its own, so callers pass
whatever profile they have, or omit it for a first-time user.
"""

from __future__ import annotations

from reality_engine.ai_gateway.application.gateway import AIGateway
from reality_engine.ai_gateway.domain.ports import ModelTier
from reality_engine.pipeline.agents._prompting import format_context
from reality_engine.pipeline.domain.schemas import EmotionsOutput, PsychologyOutput

_SYSTEM_PROMPT = (
    "Basado en la decisión, el estado emocional detectado y (si existe) el "
    "historial de sesgos previos de este usuario, identifica qué sesgos "
    "cognitivos podrían estar distorsionando su evaluación de las opciones. "
    "Para cada sesgo, explica en una frase cómo se manifiesta específicamente "
    "en este caso. No listes sesgos genéricos sin evidencia en el texto. "
    "Responde solo JSON según el esquema."
)


class PsychologyAgent:
    def __init__(self, ai_gateway: AIGateway) -> None:
        self._gateway = ai_gateway

    async def run(
        self,
        summary: str,
        emotions: EmotionsOutput,
        user_bias_profile: dict[str, object] | None = None,
    ) -> PsychologyOutput:
        return await self._gateway.generate_structured(
            tier=ModelTier.STRUCTURED_EXTRACTION,
            system_prompt=_SYSTEM_PROMPT,
            user_input=format_context(
                summary=summary,
                emotions=emotions.model_dump(),
                user_bias_profile=user_bias_profile or {},
            ),
            response_model=PsychologyOutput,
        )
