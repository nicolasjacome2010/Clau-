"""Application use cases for the decisions bounded context."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from core_api.decisions.domain.entities import Decision, DecisionStatus, DecisionVertical
from core_api.decisions.domain.exceptions import DecisionNotFoundError
from core_api.decisions.domain.repositories import DecisionRepository

_TITLE_MAX_LENGTH = 80


def _derive_placeholder_title(raw_input: str) -> str:
    """A naive truncation used until Reality Engine Agent 1 (Comprensión) is
    implemented (docs/REALITY_ENGINE.md §2, Agente 1) and can produce a real
    `decision_question`. Callers should treat `Decision.title` as
    provisional for decisions still in `draft`/`clarifying` status.
    """
    collapsed = " ".join(raw_input.split())
    if len(collapsed) <= _TITLE_MAX_LENGTH:
        return collapsed
    return collapsed[: _TITLE_MAX_LENGTH - 1].rstrip() + "…"


@dataclass(frozen=True, slots=True)
class CreateDecisionInput:
    user_id: UUID
    raw_input: str
    vertical: DecisionVertical


class CreateDecisionUseCase:
    def __init__(self, decision_repository: DecisionRepository) -> None:
        self._decisions = decision_repository

    async def execute(self, data: CreateDecisionInput) -> Decision:
        now = datetime.now(UTC)
        decision = Decision(
            id=uuid4(),
            user_id=data.user_id,
            title=_derive_placeholder_title(data.raw_input),
            vertical=data.vertical,
            status=DecisionStatus.DRAFT,
            raw_input=data.raw_input,
            created_at=now,
            updated_at=now,
        )
        return await self._decisions.create(decision)


class ListUserDecisionsUseCase:
    def __init__(self, decision_repository: DecisionRepository) -> None:
        self._decisions = decision_repository

    async def execute(
        self, user_id: UUID, *, status: DecisionStatus | None = None
    ) -> list[Decision]:
        return await self._decisions.list_for_user(user_id, status=status)


class GetUserDecisionUseCase:
    def __init__(self, decision_repository: DecisionRepository) -> None:
        self._decisions = decision_repository

    async def execute(self, decision_id: UUID, requesting_user_id: UUID) -> Decision:
        decision = await self._decisions.get_by_id(decision_id)
        if decision is None or decision.user_id != requesting_user_id:
            raise DecisionNotFoundError(decision_id)
        return decision


@dataclass(frozen=True, slots=True)
class UpdateDecisionStatusInput:
    decision_id: UUID
    requesting_user_id: UUID
    new_status: DecisionStatus


class UpdateDecisionStatusUseCase:
    """Transitions are validated by `Decision.with_status` (domain
    invariant); this use case only handles lookup/ownership and persistence.
    """

    def __init__(self, decision_repository: DecisionRepository) -> None:
        self._decisions = decision_repository

    async def execute(self, data: UpdateDecisionStatusInput) -> Decision:
        decision = await self._decisions.get_by_id(data.decision_id)
        if decision is None or decision.user_id != data.requesting_user_id:
            raise DecisionNotFoundError(data.decision_id)

        updated = decision.with_status(data.new_status, at=datetime.now(UTC))
        return await self._decisions.update(updated)
