import 'decision_outcome.dart';
import 'simulation.dart';

/// Port over the backend's `simulations` bounded context
/// (backend/src/core_api/simulations/api/router.py).
///
/// `runSimulation` is a single blocking call that can take 15-30s: the
/// backend calls Reality Engine synchronously and there is no progress
/// channel yet (docs/ARCHITECTURE.md §2.2 describes a queue + WebSocket
/// streaming that isn't built). That's why the client shows an honest
/// indeterminate wait instead of Pantalla 6's stage-by-stage animation —
/// a fake progress bar over an opaque call would be exactly the kind of
/// thing docs/UX_DESIGN.md §2 warns "rompería confianza si se estanca".
///
/// `reportOutcome` closes the loop (docs/PRD.md CU8): it hands the user's
/// account of what really happened to Agente 12, which recalibrates the
/// user's bias profile. There is deliberately **no** `getOutcome` here —
/// the backend exposes no `GET .../outcome`, so this port doesn't pretend
/// it can tell whether a decision's loop was already closed. See
/// `DecisionOutcomeController` for what that costs and how it's handled.
abstract class SimulationsRepository {
  Future<List<Simulation>> listForDecision(String decisionId);

  Future<Simulation> runSimulation(String decisionId);

  Future<DecisionOutcome> reportOutcome({
    required String decisionId,
    required String reportedOutcome,
  });
}

/// Mirrors the other ports' error type: never a leaked `DioException`.
class SimulationsRepositoryError implements Exception {
  SimulationsRepositoryError(this.message);

  final String message;

  @override
  String toString() => 'SimulationsRepositoryError: $message';
}

/// The backend's 409 on `POST /v1/decisions/{id}/outcome`: there is nothing
/// to calibrate against because the decision was never simulated to
/// completion. A distinct type because the user-facing answer is distinct —
/// "simulá primero", not "algo salió mal".
class NoCompletedSimulationError extends SimulationsRepositoryError {
  NoCompletedSimulationError(super.message);
}

/// The backend's 503: Reality Engine's `/v1/calibrate` is unreachable or
/// exhausted its providers. Transient by nature, so the user is told to
/// retry — and nothing was persisted, so retrying is safe.
class CalibrationUnavailableError extends SimulationsRepositoryError {
  CalibrationUnavailableError(super.message);
}
