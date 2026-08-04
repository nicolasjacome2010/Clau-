"""Agent 7 — Generación de Escenarios (docs/REALITY_ENGINE.md §2).

The creative core of the pipeline: 3-5 plausible future timelines derived
from the decision, each with explicit assumptions and a relative
probability. Uses the `reasoning_creative` tier — the one place in the
pipeline where model quality matters most (docs/ARCHITECTURE.md §2.6).
"""

from __future__ import annotations

from reality_engine.ai_gateway.application.gateway import AIGateway
from reality_engine.ai_gateway.domain.ports import LLMGenerationError, ModelTier
from reality_engine.pipeline.agents._language_guards import find_deterministic_future_language
from reality_engine.pipeline.agents._prompting import format_context
from reality_engine.pipeline.domain.schemas import (
    GoalsExtractionOutput,
    PsychologyOutput,
    RiskAnalysisOutput,
    ScenariosOutput,
)

_SYSTEM_PROMPT = (
    "Genera entre 3 y 5 escenarios de futuro plausibles (6-24 meses de "
    "horizonte) resultantes de esta decisión, usando el mapa de riesgos, "
    "objetivos y contexto dados. Cada escenario debe: (1) derivar de una "
    "combinación coherente de opción + supuestos externos razonables, (2) "
    "declarar sus supuestos explícitamente, (3) tener una probabilidad "
    "relativa respecto a los demás escenarios (suman 100), (4) NUNCA "
    "presentarse como un hecho futuro — usa condicional ('podrías', 'es "
    "plausible que'), nunca futuro afirmativo ('serás', 'pasará'). Responde "
    "solo JSON según el esquema."
)


def _normalize_probabilities(output: ScenariosOutput) -> ScenariosOutput:
    total = sum(s.relative_probability for s in output.scenarios)
    if total == 0 or round(total) == 100:
        return output
    return ScenariosOutput(
        scenarios=[
            s.model_copy(
                update={"relative_probability": round(s.relative_probability * 100 / total, 2)}
            )
            for s in output.scenarios
        ]
    )


class ScenarioGenerationAgent:
    def __init__(self, ai_gateway: AIGateway, *, max_language_retries: int = 1) -> None:
        self._gateway = ai_gateway
        self._max_language_retries = max_language_retries

    async def run(
        self,
        summary: str,
        goals: GoalsExtractionOutput,
        psychology: PsychologyOutput,
        risks: RiskAnalysisOutput,
    ) -> ScenariosOutput:
        user_input = format_context(
            summary=summary,
            goals=goals.model_dump(),
            psychology=psychology.model_dump(),
            risks=risks.model_dump(),
        )

        for _attempt in range(self._max_language_retries + 1):
            result = await self._gateway.generate_structured(
                tier=ModelTier.REASONING_CREATIVE,
                system_prompt=_SYSTEM_PROMPT,
                user_input=user_input,
                response_model=ScenariosOutput,
            )
            flagged = find_deterministic_future_language([s.narrative for s in result.scenarios])
            if not flagged:
                return _normalize_probabilities(result)

        raise LLMGenerationError(
            "Scenario narratives kept using deterministic future language after retries"
        )
