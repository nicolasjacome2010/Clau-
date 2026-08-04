"""Domain entities for the memory bounded context (docs/DATABASE.md §2.10-2.11).

Feeds Reality Engine's Agent 5 (Análisis Psicológico, optional
`user_bias_profile` input) and is written to by Agents 11-12 (Memoria,
Aprendizaje) once those exist — this module doesn't call the Reality
Engine itself, it's the persistence side of that future integration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class BiasObservation:
    bias: str
    score: float
    occurrences: int

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("score must be between 0 and 1")
        if self.occurrences < 1:
            raise ValueError("occurrences must be at least 1")


@dataclass(frozen=True, slots=True)
class UserBiasProfile:
    user_id: UUID
    biases: tuple[BiasObservation, ...] = field(default_factory=tuple)
    calibration_score: float = 0.0
    updated_at: datetime | None = None

    def with_bias_observation(
        self, bias: str, confidence: float, *, at: datetime
    ) -> UserBiasProfile:
        """Incremental update via weighted moving average — never a full
        overwrite (docs/REALITY_ENGINE.md §2, Agente 5/12: "actualiza
        user_bias_profile de forma incremental").
        """
        existing = next((b for b in self.biases if b.bias == bias), None)
        if existing is None:
            updated = BiasObservation(bias=bias, score=confidence, occurrences=1)
        else:
            new_occurrences = existing.occurrences + 1
            new_score = (existing.score * existing.occurrences + confidence) / new_occurrences
            updated = BiasObservation(bias=bias, score=new_score, occurrences=new_occurrences)

        remaining = tuple(b for b in self.biases if b.bias != bias)
        return UserBiasProfile(
            user_id=self.user_id,
            biases=(*remaining, updated),
            calibration_score=self.calibration_score,
            updated_at=at,
        )

    def with_calibration_delta(self, delta: float, *, at: datetime) -> UserBiasProfile:
        """Simple exponential moving average toward the new delta — a
        starting formula, not a validated calibration model (same
        humility as elsewhere in this codebase: documented, tunable).
        """
        new_score = self.calibration_score * 0.8 + delta * 0.2
        return UserBiasProfile(
            user_id=self.user_id,
            biases=self.biases,
            calibration_score=new_score,
            updated_at=at,
        )


@dataclass(frozen=True, slots=True)
class MemoryEmbedding:
    id: UUID
    user_id: UUID
    decision_id: UUID | None
    summary_text: str
    embedding: tuple[float, ...]
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.summary_text.strip():
            raise ValueError("summary_text cannot be empty")
        if not self.embedding:
            raise ValueError("embedding cannot be empty")
