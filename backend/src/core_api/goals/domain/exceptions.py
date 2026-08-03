"""Domain-level errors for the goals bounded context."""

from __future__ import annotations

from uuid import UUID


class GoalsDomainError(Exception):
    """Base class for all goals domain errors."""


class GoalNotFoundError(GoalsDomainError):
    """Raised both when a goal truly doesn't exist and when it exists but
    belongs to a different user — callers must not distinguish the two in
    any user-facing response, to avoid leaking the existence of other
    users' goals (see goals/api/router.py).
    """

    def __init__(self, goal_id: UUID) -> None:
        self.goal_id = goal_id
        super().__init__(f"Goal {goal_id} was not found")
