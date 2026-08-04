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


class NoCompletedSimulationError(SimulationsDomainError):
    """Raised when reporting an outcome for a decision that has no
    COMPLETED simulation to calibrate against — there is nothing for
    Reality Engine's Agent 12 to compare the reported outcome to.
    """

    def __init__(self, decision_id: UUID) -> None:
        self.decision_id = decision_id
        super().__init__(f"Decision {decision_id} has no completed simulation to report against")
