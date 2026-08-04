"""Sequential orchestrator wiring Agents 0-6 (docs/REALITY_ENGINE.md §1).

Agents 7-12 (Generación de Escenarios onward) are not implemented yet — see
docs/REALITY_ENGINE.md and reality_engine/README.md for what's left. This
orchestrator covers the *analysis* half of the pipeline: everything that
must happen before scenario generation can.

Execution is sequential for now, even though the spec notes Agents 1-6 can
partially parallelize once their data dependencies are met (e.g. Riesgos
only needs Comprensión, not Resumen) — that's a latency optimization for
when this pipeline actually needs to hit the sub-25s target from
docs/PRD.md §3, not a correctness requirement, so it's deferred rather
than added speculatively.
"""

from __future__ import annotations

from pydantic import BaseModel

from reality_engine.ai_gateway.application.gateway import AIGateway
from reality_engine.pipeline.agents.comprehension import ComprehensionAgent
from reality_engine.pipeline.agents.emotions import EmotionsAgent
from reality_engine.pipeline.agents.goals_extraction import GoalsExtractionAgent
from reality_engine.pipeline.agents.psychology import PsychologyAgent
from reality_engine.pipeline.agents.risk_analysis import RiskAnalysisAgent
from reality_engine.pipeline.agents.safety_gate import SafetyGateAgent
from reality_engine.pipeline.agents.summary import SummaryAgent
from reality_engine.pipeline.domain.schemas import (
    ComprehensionOutput,
    EmotionsOutput,
    GoalsExtractionOutput,
    PsychologyOutput,
    RiskAnalysisOutput,
    SafetyGateOutput,
    SummaryOutput,
)


class AnalysisResult(BaseModel):
    safety: SafetyGateOutput
    comprehension: ComprehensionOutput | None = None
    summary: SummaryOutput | None = None
    goals: GoalsExtractionOutput | None = None
    emotions: EmotionsOutput | None = None
    psychology: PsychologyOutput | None = None
    risks: RiskAnalysisOutput | None = None


class AnalysisPipeline:
    """Stops immediately after Agent 0 if it doesn't clear the input as
    safe to proceed (docs/REALITY_ENGINE.md §1: Agent 0 "puede terminar el
    pipeline anticipadamente").
    """

    def __init__(self, ai_gateway: AIGateway) -> None:
        self._safety_gate = SafetyGateAgent(ai_gateway)
        self._comprehension = ComprehensionAgent(ai_gateway)
        self._summary = SummaryAgent(ai_gateway)
        self._goals = GoalsExtractionAgent(ai_gateway)
        self._emotions = EmotionsAgent(ai_gateway)
        self._psychology = PsychologyAgent(ai_gateway)
        self._risks = RiskAnalysisAgent(ai_gateway)

    async def run(
        self, raw_input: str, *, declared_goals: list[str] | None = None
    ) -> AnalysisResult:
        safety = await self._safety_gate.run(raw_input)
        if not safety.safe_to_proceed:
            return AnalysisResult(safety=safety)

        comprehension = await self._comprehension.run(raw_input)
        summary = await self._summary.run(comprehension)
        goals = await self._goals.run(summary.summary, declared_goals or [])
        emotions = await self._emotions.run(raw_input, summary.summary)
        psychology = await self._psychology.run(summary.summary, emotions)
        risks = await self._risks.run(comprehension)

        return AnalysisResult(
            safety=safety,
            comprehension=comprehension,
            summary=summary,
            goals=goals,
            emotions=emotions,
            psychology=psychology,
            risks=risks,
        )
