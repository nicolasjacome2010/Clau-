"""Agent 12 — Aprendizaje (docs/REALITY_ENGINE.md §2).

Runs on-demand, not as part of the main simulation pipeline: only when a
user reports what actually happened with a past decision (docs/PRD.md
CU8, "cierre de ciclo"). Exposed via its own endpoint (`POST
/v1/calibrate`), never through `AnalysisPipeline`/`SimulationPipeline`.
"""

from __future__ import annotations

from reality_engine.ai_gateway.application.gateway import AIGateway
from reality_engine.ai_gateway.domain.ports import ModelTier
from reality_engine.pipeline.agents._prompting import format_context
from reality_engine.pipeline.domain.schemas import (
    CalibrationOutput,
    RankingOutput,
    ScenariosOutput,
)

_SYSTEM_PROMPT = (
    "Dado el resultado real reportado por el usuario y los escenarios "
    "previamente generados, identifica cuál escenario se acercó más a lo "
    "ocurrido y en qué se equivocó la simulación (supuestos incorrectos, "
    "sesgo no detectado, riesgo subestimado/sobrestimado). Sé específico y "
    "honesto sobre los errores del sistema. Si lo ocurrido no se parece a "
    "ningún escenario generado, dejalo explícito (closest_scenario_id "
    "puede ser null) en vez de forzar una coincidencia. Responde solo JSON "
    "según el esquema."
)


class LearningAgent:
    def __init__(self, ai_gateway: AIGateway) -> None:
        self._gateway = ai_gateway

    async def run(
        self,
        reported_outcome: str,
        original_scenarios: ScenariosOutput,
        original_ranking: RankingOutput,
    ) -> CalibrationOutput:
        return await self._gateway.generate_structured(
            tier=ModelTier.STRUCTURED_EXTRACTION,
            system_prompt=_SYSTEM_PROMPT,
            user_input=format_context(
                reported_outcome=reported_outcome,
                original_scenarios=original_scenarios.model_dump(),
                original_ranking=original_ranking.model_dump(),
            ),
            response_model=CalibrationOutput,
        )
