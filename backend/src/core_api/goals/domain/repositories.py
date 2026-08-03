"""Repository interface (port) for the goals bounded context."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from core_api.goals.domain.entities import Goal


class GoalRepository(ABC):
    @abstractmethod
    async def get_by_id(self, goal_id: UUID) -> Goal | None: ...

    @abstractmethod
    async def list_for_user(self, user_id: UUID, *, active_only: bool = True) -> list[Goal]: ...

    @abstractmethod
    async def create(self, goal: Goal) -> Goal: ...

    @abstractmethod
    async def update(self, goal: Goal) -> Goal: ...
