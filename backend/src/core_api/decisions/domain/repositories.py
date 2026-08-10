"""Repository interface (port) for the decisions bounded context."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from core_api.decisions.domain.entities import Decision, DecisionStatus


class DecisionRepository(ABC):
    @abstractmethod
    async def get_by_id(self, decision_id: UUID) -> Decision | None: ...

    @abstractmethod
    async def list_for_user(
        self, user_id: UUID, *, status: DecisionStatus | None = None
    ) -> list[Decision]: ...

    @abstractmethod
    async def create(self, decision: Decision) -> Decision: ...

    @abstractmethod
    async def update(self, decision: Decision) -> Decision: ...
