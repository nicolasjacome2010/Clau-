"""Domain entities for the goals bounded context.

A Goal is what a user declares they're optimizing for (docs/PRD.md §7,
Épica A) and is later consumed by Reality Engine Agent 3 — Extracción de
Objetivos (docs/REALITY_ENGINE.md) as a weighted prior.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Goal:
    id: UUID
    user_id: UUID
    name: str
    default_weight: int
    is_active: bool
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Goal name cannot be empty")
        if not 0 <= self.default_weight <= 100:
            raise ValueError("default_weight must be between 0 and 100")
