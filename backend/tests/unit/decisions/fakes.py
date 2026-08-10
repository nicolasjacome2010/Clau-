"""In-memory fake of the decisions repository, used only by unit tests."""

from __future__ import annotations

from uuid import UUID

from core_api.decisions.domain.entities import Decision, DecisionStatus
from core_api.decisions.domain.repositories import DecisionRepository


class InMemoryDecisionRepository(DecisionRepository):
    def __init__(self) -> None:
        self._decisions: dict[UUID, Decision] = {}

    async def get_by_id(self, decision_id: UUID) -> Decision | None:
        return self._decisions.get(decision_id)

    async def list_for_user(
        self, user_id: UUID, *, status: DecisionStatus | None = None
    ) -> list[Decision]:
        return [
            d
            for d in self._decisions.values()
            if d.user_id == user_id and (status is None or d.status == status)
        ]

    async def create(self, decision: Decision) -> Decision:
        self._decisions[decision.id] = decision
        return decision

    async def update(self, decision: Decision) -> Decision:
        if decision.id not in self._decisions:
            raise ValueError(f"Cannot update non-existent decision {decision.id}")
        self._decisions[decision.id] = decision
        return decision
