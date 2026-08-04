"""Domain-level errors for the simulations bounded context."""

from __future__ import annotations

from uuid import UUID


class SimulationsDomainError(Exception):
    """Base class for all simulations domain errors."""


class SimulationNotFoundError(SimulationsDomainError):
    """Raised both when a simulation truly doesn't exist and when it
    belongs to a decision owned by a different user — see
    goals/domain/exceptions.py for why callers must not distinguish the
    two in any user-facing response.
    """

    def __init__(self, simulation_id: UUID) -> None:
        self.simulation_id = simulation_id
        super().__init__(f"Simulation {simulation_id} was not found")
