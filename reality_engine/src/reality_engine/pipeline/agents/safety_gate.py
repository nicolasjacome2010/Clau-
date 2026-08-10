"""Agent 0 — Risk & Safety Gate (docs/REALITY_ENGINE.md §2).

Combines a deterministic keyword/pattern pre-screen with an LLM classifier,
per the spec: "combina un clasificador de IA con reglas deterministas...
nunca depende solo del LLM". The deterministic pass runs first and is
purely additive — it can only escalate risk, never lower it, and it never
calls out to a model, so it's fast and available even if the AI Gateway is
degraded.

LIMITATION (explicitly flagged, not hidden): `_ACUTE_RISK_PATTERNS` below is
a starting point, not a clinically or legally validated list. Before any
production launch this must be reviewed with a mental-health/legal
professional per docs/PRD.md §18 ("Riesgo: casos de alto riesgo emocional
mal manejados por el pipeline").
"""

from __future__ import annotations

import re

from reality_engine.ai_gateway.application.gateway import AIGateway
from reality_engine.ai_gateway.domain.ports import LLMGenerationError, ModelTier
from reality_engine.pipeline.domain.schemas import RecommendedAction, RiskLevel, SafetyGateOutput

_SYSTEM_PROMPT = (
    "Eres un clasificador de seguridad. NO respondas a la decisión del usuario. "
    "Tu única tarea es clasificar el texto en una de estas categorías de riesgo: "
    "'none', 'moderate_distress', 'acute_risk'. 'acute_risk' incluye cualquier "
    "mención de autolesión, suicidio, daño a otra persona, abuso o crisis médica "
    "aguda. Ante la duda, clasifica hacia arriba (más riesgo), nunca hacia abajo. "
    "Responde solo JSON según el esquema."
)

# Deliberately conservative and bilingual (es/en). Word-boundary patterns to
# avoid matching inside unrelated words.
_ACUTE_RISK_PATTERNS: list[re.Pattern[str]] = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\bsuicid\w*",
        r"\bquitarme la vida\b",
        r"\bacabar con (mi|su) vida\b",
        r"\bautolesi\w*",
        r"\bhacerme daño\b",
        r"\bkill myself\b",
        r"\bend my life\b",
        r"\bself[\s-]?harm\w*",
        r"\bhacerle daño a\b",
        r"\bmatar\w*\s+a\b",
        r"\bhurt (him|her|them)\b",
        r"\bkill (him|her|them)\b",
    ]
]


def _deterministic_prescreen(raw_input: str) -> list[str]:
    return [
        pattern.pattern
        for pattern in _ACUTE_RISK_PATTERNS
        if pattern.search(raw_input) is not None
    ]


_HALT = SafetyGateOutput(
    risk_level=RiskLevel.ACUTE_RISK,
    signals_detected=[],
    safe_to_proceed=False,
    recommended_action=RecommendedAction.HALT_AND_REFER,
)


class SafetyGateAgent:
    def __init__(self, ai_gateway: AIGateway) -> None:
        self._gateway = ai_gateway

    async def run(self, raw_input: str) -> SafetyGateOutput:
        matched_patterns = _deterministic_prescreen(raw_input)
        if matched_patterns:
            return _HALT.model_copy(update={"signals_detected": matched_patterns})

        try:
            return await self._gateway.generate_structured(
                tier=ModelTier.SAFETY_CLASSIFICATION,
                system_prompt=_SYSTEM_PROMPT,
                user_input=raw_input,
                response_model=SafetyGateOutput,
            )
        except LLMGenerationError:
            # Fail-safe, not fail-open (docs/REALITY_ENGINE.md §2, Agente 0
            # errors: "esto se resuelve escalando siempre a la categoría más
            # conservadora").
            return _HALT.model_copy(update={"signals_detected": ["classification_failed"]})
