"""Structured I/O contracts for pipeline agents.

Pydantic models, not dataclasses: they double as the JSON Schema handed to
`AIGateway.generate_structured` (docs/REALITY_ENGINE.md §2 — every agent's
output is validated JSON, never free text).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class RiskLevel(StrEnum):
    NONE = "none"
    MODERATE_DISTRESS = "moderate_distress"
    ACUTE_RISK = "acute_risk"


class RecommendedAction(StrEnum):
    PROCEED = "proceed"
    PROCEED_WITH_CARE = "proceed_with_care"
    HALT_AND_REFER = "halt_and_refer"


class SafetyGateOutput(BaseModel):
    """docs/REALITY_ENGINE.md §2, Agente 0 — Risk & Safety Gate."""

    risk_level: RiskLevel
    signals_detected: list[str] = Field(default_factory=list)
    safe_to_proceed: bool
    recommended_action: RecommendedAction


class FactualContext(BaseModel):
    entities: list[str] = Field(default_factory=list)
    deadlines: list[str] = Field(default_factory=list)
    figures: list[str] = Field(default_factory=list)


class ComprehensionOutput(BaseModel):
    """docs/REALITY_ENGINE.md §2, Agente 1 — Comprensión."""

    decision_question: str
    explicit_options: list[str] = Field(default_factory=list)
    factual_context: FactualContext = Field(default_factory=FactualContext)
    missing_info: list[str] = Field(default_factory=list)
    requires_clarification: bool


class SummaryOutput(BaseModel):
    """docs/REALITY_ENGINE.md §2, Agente 2 — Resumen."""

    summary: str = Field(max_length=900)  # ~120 words, generous character ceiling


class GoalSource(StrEnum):
    EXPLICIT = "explicit"
    INFERRED = "inferred"


class ExtractedGoal(BaseModel):
    name: str
    weight: int = Field(ge=0, le=100)
    source: GoalSource


class GoalsExtractionOutput(BaseModel):
    """docs/REALITY_ENGINE.md §2, Agente 3 — Extracción de Objetivos."""

    goals: list[ExtractedGoal] = Field(default_factory=list)


class EmotionalLoad(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DetectedEmotion(BaseModel):
    label: str
    intensity: float = Field(ge=0.0, le=1.0)
    evidence: str


class EmotionsOutput(BaseModel):
    """docs/REALITY_ENGINE.md §2, Agente 4 — Extracción de Emociones."""

    emotions: list[DetectedEmotion] = Field(default_factory=list)
    overall_emotional_load: EmotionalLoad


class PsychologicalReadiness(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DetectedBias(BaseModel):
    bias: str
    manifestation: str
    confidence: float = Field(ge=0.0, le=1.0)


class PsychologyOutput(BaseModel):
    """docs/REALITY_ENGINE.md §2, Agente 5 — Análisis Psicológico."""

    biases_detected: list[DetectedBias] = Field(default_factory=list)
    psychological_readiness: PsychologicalReadiness


class RiskSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class OptionRisk(BaseModel):
    type: str
    severity: RiskSeverity
    reversibility: RiskSeverity


class OptionRiskMap(BaseModel):
    option: str
    risks: list[OptionRisk] = Field(default_factory=list)


class RiskAnalysisOutput(BaseModel):
    """docs/REALITY_ENGINE.md §2, Agente 6 — Análisis de Riesgos."""

    risk_map: list[OptionRiskMap] = Field(default_factory=list)


class Scenario(BaseModel):
    id: str
    title: str
    based_on_option: str
    narrative: str
    assumptions: list[str] = Field(default_factory=list)
    relative_probability: float = Field(ge=0, le=100)
    time_horizon_months: int = Field(ge=1, le=60)


class ScenariosOutput(BaseModel):
    """docs/REALITY_ENGINE.md §2, Agente 7 — Generación de Escenarios."""

    scenarios: list[Scenario] = Field(min_length=3, max_length=5)


class GoalAlignmentScore(BaseModel):
    goal: str
    score: int = Field(ge=0, le=100)
    justification: str


class ScenarioComparison(BaseModel):
    scenario_id: str
    goal_alignment_scores: list[GoalAlignmentScore] = Field(default_factory=list)
    risk_score: float = Field(ge=0, le=100)
    reversibility_score: float = Field(ge=0, le=100)


class ComparisonOutput(BaseModel):
    """docs/REALITY_ENGINE.md §2, Agente 8 — Comparación."""

    comparison_matrix: list[ScenarioComparison] = Field(default_factory=list)


class RankedScenario(BaseModel):
    scenario_id: str
    final_score: float
    rank: int


class RankingOutput(BaseModel):
    """docs/REALITY_ENGINE.md §2, Agente 9 — Ranking.

    Not an LLM call: a pure aggregation function over Agent 8's output (see
    `pipeline/agents/ranking.py`), included here only so it has the same
    typed-contract shape as every other agent's output.
    """

    ranking: list[RankedScenario] = Field(default_factory=list)


class SynthesisOutput(BaseModel):
    """docs/REALITY_ENGINE.md §2, Agente 10 — Síntesis."""

    synthesis: str = Field(max_length=1800)  # ~250 words, generous character ceiling
    reflective_question: str
