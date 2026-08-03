"""In-memory fake of the goals repository, used only by unit tests."""

from __future__ import annotations

from uuid import UUID

from core_api.goals.domain.entities import Goal
from core_api.goals.domain.repositories import GoalRepository


class InMemoryGoalRepository(GoalRepository):
    def __init__(self) -> None:
        self._goals: dict[UUID, Goal] = {}

    async def get_by_id(self, goal_id: UUID) -> Goal | None:
        return self._goals.get(goal_id)

    async def list_for_user(self, user_id: UUID, *, active_only: bool = True) -> list[Goal]:
        return [
            goal
            for goal in self._goals.values()
            if goal.user_id == user_id and (goal.is_active or not active_only)
        ]

    async def create(self, goal: Goal) -> Goal:
        self._goals[goal.id] = goal
        return goal

    async def update(self, goal: Goal) -> Goal:
        if goal.id not in self._goals:
            raise ValueError(f"Cannot update non-existent goal {goal.id}")
        self._goals[goal.id] = goal
        return goal
