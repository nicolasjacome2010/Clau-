"""Domain-level errors for the decisions bounded context."""

from __future__ import annotations

from uuid import UUID


class DecisionsDomainError(Exception):
    """Base class for all decisions domain errors."""


class DecisionNotFoundError(DecisionsDomainError):
    """Raised both when a decision truly doesn't exist and when it exists
    but belongs to a different user — see goals/domain/exceptions.py for
    why callers must not distinguish the two in any user-facing response.
    """

    def __init__(self, decision_id: UUID) -> None:
        self.decision_id = decision_id
        super().__init__(f"Decision {decision_id} was not found")
