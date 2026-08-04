"""Sequential orchestrator wiring the full implemented pipeline, Agents 0-11
(docs/REALITY_ENGINE.md §1). Agent 12 (Aprendizaje) is deliberately not
wired in here — see `pipeline/agents/learning.py`'s docstring: it runs
on-demand from `POST /v1/calibrate`, never as part of a simulation run.

Execution is sequential for now, even though the spec notes some agents can
partially parallelize once their data dependencies are met (e.g. Riesgos
only needs Comprensión, not Resumen) — that's a latency optimization for
when this pipeline actually needs to hit the sub-25s target from
docs/PRD.md §3, not a correctness requirement, so it's deferred rather
than added speculatively.
"""

from __future__ import annotations

from pydantic import BaseModel

from reality_engine.ai_gateway.application.gateway import AIGateway
from reality_engine.ai_gateway.domain.ports import EmbeddingGenerationError, LLMGenerationError
from reality_engine.pipeline.agents.comparison import ComparisonAgent
from reality_engine.pipeline.agents.comprehension import ComprehensionAgent
from reality_engine.pipeline.agents.emotions import EmotionsAgent
from reality_engine.pipeline.agents.goals_extraction import GoalsExtractionAgent
from reality_engine.pipeline.agents.memory import MemoryAgent
from reality_engine.pipeline.agents.psychology import PsychologyAgent
from reality_engine.pipeline.agents.ranking import RankingAgent
from reality_engine.pipeline.agents.risk_analysis import RiskAnalysisAgent
from reality_engine.pipeline.agents.safety_gate import SafetyGateAgent
from reality_engine.pipeline.agents.scenario_generation import ScenarioGenerationAgent
from reality_engine.pipeline.agents.summary import SummaryAgent
from reality_engine.pipeline.agents.synthesis import SynthesisAgent
from reality_engine.pipeline.domain.schemas import (
    ComparisonOutput,
    ComprehensionOutput,
    EmotionsOutput,
    GoalsExtractionOutput,
    PsychologyOutput,
    RankingOutput,
    RiskAnalysisOutput,
    SafetyGateOutput,
    ScenariosOutput,
    SummaryOutput,
    SynthesisOutput,
)


class AnalysisResult(BaseModel):
    """Agents 0-6 — everything that must happen before scenario generation."""

    safety: SafetyGateOutput
    comprehension: ComprehensionOutput | None = None
    summary: SummaryOutput | None = None
    goals: GoalsExtractionOutput | None = None
    emotions: EmotionsOutput | None = None
    psychology: PsychologyOutput | None = None
    risks: RiskAnalysisOutput | None = None


class SimulationMemoryResult(BaseModel):
    """Agent 11's output plus the embedding computed from it — the whole
    payload Core API's `memory` module needs to persist a `MemoryEmbedding`
    (see docs/DATABASE.md §2.11).
    """

    summary_text: str
    embedding: list[float]


class SimulationResult(BaseModel):
    """Agents 0-11 — the full simulation as far as this service goes today.

    `scenarios`/`comparison`/`ranking`/`synthesis` stay `None` whenever the
    analysis half didn't clear Agent 0 as safe to proceed. `memory` stays
    `None` either for that same reason, or — deliberately — whenever Agent
    11 or the embedding call fails: storing a memory is an enhancement on
    top of a completed simulation, never a reason to fail the simulation
    itself (see `SimulationPipeline.run`).
    """

    analysis: AnalysisResult
    scenarios: ScenariosOutput | None = None
    comparison: ComparisonOutput | None = None
    ranking: RankingOutput | None = None
    synthesis: SynthesisOutput | None = None
    memory: SimulationMemoryResult | None = None


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


class SimulationPipeline:
    """Runs `AnalysisPipeline` (Agents 0-6), then — only if it cleared
    Agent 0 as safe — continues through Agents 7-11 to produce the full
    ranked, synthesized result plus a storable memory.
    """

    def __init__(self, ai_gateway: AIGateway) -> None:
        self._gateway = ai_gateway
        self._analysis = AnalysisPipeline(ai_gateway)
        self._scenarios = ScenarioGenerationAgent(ai_gateway)
        self._comparison = ComparisonAgent(ai_gateway)
        self._ranking = RankingAgent()
        self._synthesis = SynthesisAgent(ai_gateway)
        self._memory = MemoryAgent(ai_gateway)

    async def run(
        self, raw_input: str, *, declared_goals: list[str] | None = None
    ) -> SimulationResult:
        analysis = await self._analysis.run(raw_input, declared_goals=declared_goals)
        if not analysis.safety.safe_to_proceed:
            return SimulationResult(analysis=analysis)

        # The following are guaranteed non-None whenever safety.safe_to_proceed
        # is True — AnalysisPipeline.run only returns early (leaving them
        # None) on the unsafe branch, handled above.
        assert analysis.summary is not None
        assert analysis.goals is not None
        assert analysis.psychology is not None
        assert analysis.risks is not None

        scenarios = await self._scenarios.run(
            analysis.summary.summary, analysis.goals, analysis.psychology, analysis.risks
        )
        comparison = await self._comparison.run(scenarios, analysis.goals, analysis.risks)
        ranking = self._ranking.run(comparison, analysis.goals)
        assert analysis.emotions is not None
        synthesis = await self._synthesis.run(
            ranking, comparison, analysis.psychology, analysis.emotions
        )
        memory = await self._try_build_memory(analysis, ranking)

        return SimulationResult(
            analysis=analysis,
            scenarios=scenarios,
            comparison=comparison,
            ranking=ranking,
            synthesis=synthesis,
            memory=memory,
        )

    async def _try_build_memory(
        self, analysis: AnalysisResult, ranking: RankingOutput
    ) -> SimulationMemoryResult | None:
        assert analysis.summary is not None
        assert analysis.goals is not None
        assert analysis.psychology is not None
        try:
            memory_output = await self._memory.run(
                analysis.summary.summary, analysis.goals, analysis.psychology, ranking
            )
            embedding = await self._gateway.embed(memory_output.embedding_ready_text)
        except (LLMGenerationError, EmbeddingGenerationError):
            return None
        return SimulationMemoryResult(
            summary_text=memory_output.memory_summary, embedding=embedding
        )
