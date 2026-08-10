"""Application use cases for the goals bounded context."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from core_api.goals.domain.entities import Goal
from core_api.goals.domain.exceptions import GoalNotFoundError
from core_api.goals.domain.repositories import GoalRepository


@dataclass(frozen=True, slots=True)
class CreateGoalInput:
    user_id: UUID
    name: str
    default_weight: int = 50


class CreateGoalUseCase:
    def __init__(self, goal_repository: GoalRepository) -> None:
        self._goals = goal_repository

    async def execute(self, data: CreateGoalInput) -> Goal:
        goal = Goal(
            id=uuid4(),
            user_id=data.user_id,
            name=data.name.strip(),
            default_weight=data.default_weight,
            is_active=True,
            created_at=datetime.now(UTC),
        )
        return await self._goals.create(goal)


class ListActiveGoalsUseCase:
    def __init__(self, goal_repository: GoalRepository) -> None:
        self._goals = goal_repository

    async def execute(self, user_id: UUID) -> list[Goal]:
        return await self._goals.list_for_user(user_id, active_only=True)


@dataclass(frozen=True, slots=True)
class UpdateGoalInput:
    goal_id: UUID
    requesting_user_id: UUID
    name: str | None = None
    default_weight: int | None = None
    is_active: bool | None = None


class UpdateGoalUseCase:
    """Handles rename, reweight, and activate/deactivate as a single upsert
    of an existing goal — a dedicated `DeactivateGoalUseCase` would just be
    this same code with `is_active=False` hardcoded, so it isn't worth a
    separate class (see CLAUDE.md: no premature abstractions).
    """

    def __init__(self, goal_repository: GoalRepository) -> None:
        self._goals = goal_repository

    async def execute(self, data: UpdateGoalInput) -> Goal:
        existing = await self._goals.get_by_id(data.goal_id)
        if existing is None or existing.user_id != data.requesting_user_id:
            raise GoalNotFoundError(data.goal_id)

        updated = Goal(
            id=existing.id,
            user_id=existing.user_id,
            name=(data.name.strip() if data.name is not None else existing.name),
            default_weight=(
                data.default_weight if data.default_weight is not None else existing.default_weight
            ),
            is_active=(data.is_active if data.is_active is not None else existing.is_active),
            created_at=existing.created_at,
        )
        return await self._goals.update(updated)
