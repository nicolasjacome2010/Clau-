"""Repository interface (port) for the simulations bounded context.

No `update`: a Simulation is a historical record of one pipeline run,
never mutated after creation (see domain/entities.py).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from core_api.simulations.domain.entities import DecisionOutcome, Simulation


class SimulationRepository(ABC):
    @abstractmethod
    async def get_by_id(self, simulation_id: UUID) -> Simulation | None: ...

    @abstractmethod
    async def list_for_decision(self, decision_id: UUID) -> list[Simulation]: ...

    @abstractmethod
    async def create(self, simulation: Simulation) -> Simulation: ...


class DecisionOutcomeRepository(ABC):
    """A Decision has at most one reported outcome (docs/DATABASE.md §2.9)
    — `get_by_decision_id`, not a `list_for_decision`, mirrors that
    one-to-zero-or-one cardinality.
    """

    @abstractmethod
    async def get_by_decision_id(self, decision_id: UUID) -> DecisionOutcome | None: ...

    @abstractmethod
    async def list_for_decisions(self, decision_ids: Sequence[UUID]) -> list[DecisionOutcome]:
        """Every reported outcome among the given decisions, in one query.

        Takes ids rather than a user id on purpose: `decision_outcomes` has
        no `user_id` column, and joining `decisions` here would reach into
        another bounded context's table from inside this one's repository.
        Resolving "which decisions are mine" stays in the use case, which
        is allowed to depend on both contexts' interfaces (see
        `ListDecisionOutcomesUseCase`).
        """

    @abstractmethod
    async def create(self, outcome: DecisionOutcome) -> DecisionOutcome: ...
