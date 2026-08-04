"""Repository interface (port) for the simulations bounded context.

No `update`: a Simulation is a historical record of one pipeline run,
never mutated after creation (see domain/entities.py).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from core_api.simulations.domain.entities import Simulation


class SimulationRepository(ABC):
    @abstractmethod
    async def get_by_id(self, simulation_id: UUID) -> Simulation | None: ...

    @abstractmethod
    async def list_for_decision(self, decision_id: UUID) -> list[Simulation]: ...

    @abstractmethod
    async def create(self, simulation: Simulation) -> Simulation: ...
