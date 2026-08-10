"""Domain entities for the decisions bounded context.

`Decision` is the aggregate root of the product (docs/PRD.md — "cada
decisión vive como un objeto persistente"). It persists across multiple
Reality Engine simulations (not yet implemented — see docs/REALITY_ENGINE.md)
and enforces its own status lifecycle as an invariant, per
docs/ARCHITECTURE.md §4 ("agregados con invariantes protegidas en el
dominio").
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class DecisionVertical(StrEnum):
    CAREER = "career"
    RELATIONSHIPS = "relationships"
    FINANCE = "finance"
    BUSINESS = "business"
    RELOCATION = "relocation"
    CONFLICT = "conflict"


class DecisionStatus(StrEnum):
    DRAFT = "draft"
    CLARIFYING = "clarifying"
    SIMULATING = "simulating"
    COMPLETED = "completed"
    ARCHIVED = "archived"


# docs/DATABASE.md §2.4. `archived` is terminal: once archived a decision is
# read-only history, matching the "Archivadas" grouping in the "Mis
# Decisiones" screen (docs/UX_DESIGN.md, pantalla 10).
_ALLOWED_STATUS_TRANSITIONS: dict[DecisionStatus, frozenset[DecisionStatus]] = {
    DecisionStatus.DRAFT: frozenset({DecisionStatus.CLARIFYING, DecisionStatus.ARCHIVED}),
    DecisionStatus.CLARIFYING: frozenset(
        {DecisionStatus.SIMULATING, DecisionStatus.DRAFT, DecisionStatus.ARCHIVED}
    ),
    DecisionStatus.SIMULATING: frozenset({DecisionStatus.COMPLETED, DecisionStatus.ARCHIVED}),
    DecisionStatus.COMPLETED: frozenset({DecisionStatus.ARCHIVED}),
    DecisionStatus.ARCHIVED: frozenset(),
}


class InvalidStatusTransitionError(ValueError):
    def __init__(self, current: DecisionStatus, requested: DecisionStatus) -> None:
        self.current = current
        self.requested = requested
        super().__init__(
            f"Cannot transition decision from '{current.value}' to '{requested.value}'"
        )


@dataclass(frozen=True, slots=True)
class Decision:
    id: UUID
    user_id: UUID
    title: str
    vertical: DecisionVertical
    status: DecisionStatus
    raw_input: str
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if not self.raw_input.strip():
            raise ValueError("raw_input cannot be empty")

    def with_status(self, new_status: DecisionStatus, *, at: datetime) -> Decision:
        if new_status not in _ALLOWED_STATUS_TRANSITIONS[self.status]:
            raise InvalidStatusTransitionError(self.status, new_status)
        return replace(self, status=new_status, updated_at=at)
