import 'decision_outcome.dart';
import 'simulation.dart';
import 'simulation_progress.dart';

/// Port over the backend's `simulations` bounded context
/// (backend/src/core_api/simulations/api/router.py).
///
/// `runSimulation` is a single blocking call that can take 15-30s: the
/// backend calls Reality Engine synchronously. `runSimulationStream` is the
/// same run over `POST .../simulations/stream`'s NDJSON body, reporting
/// each Reality Engine agent as it starts/finishes (docs/UX_DESIGN.md
/// Pantalla 6) — `DecisionSimulationController.run()` uses this one, so the
/// screen can light up real stages instead of the indeterminate wait a
/// blocking call would force. `runSimulation` stays on the port too: it's
/// still a real, separately useful backend endpoint, not dead code kept
/// around out of caution.
///
/// `reportOutcome` closes the loop (docs/PRD.md CU8): it hands the user's
/// account of what really happened to Agente 12, which recalibrates the
/// user's bias profile. `listOutcomes` is how the client knows which loops
/// are already closed — a collection, mirroring `GET /v1/outcomes`, because
/// the question ("which of my decisions are still open?") is asked by a
/// list screen and a per-decision read would be an N+1 against it.
abstract class SimulationsRepository {
  Future<List<Simulation>> listForDecision(String decisionId);

  Future<Simulation> runSimulation(String decisionId);

  /// Throws `SimulationsRepositoryError` (as a stream error, not a thrown
  /// `Future`) if the request itself fails before any bytes arrive — an
  /// ownership 404 in particular, since the backend checks that before its
  /// stream starts precisely so this stays a real error and not a line
  /// inside an already-200 body.
  Stream<SimulationProgressEvent> runSimulationStream(String decisionId);

  Future<List<DecisionOutcome>> listOutcomes();

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

/// A 409 from `POST /v1/decisions/{id}/outcome`.
///
/// The backend answers 409 for two different conflicts — the decision has
/// no completed simulation to calibrate against, and the loop was already
/// closed — and both carry only a prose `detail`. This type deliberately
/// does not try to tell them apart by matching that string across a service
/// boundary: `DecisionOutcomeController` resolves the ambiguity by asking
/// the source of truth instead (re-reading `GET /v1/outcomes` and looking
/// for this decision), which is correct whatever the wording ever becomes.
class OutcomeConflictError extends SimulationsRepositoryError {
  OutcomeConflictError(super.message);
}

/// The backend's 503: Reality Engine's `/v1/calibrate` is unreachable or
/// exhausted its providers. Transient by nature, so the user is told to
/// retry — and nothing was persisted, so retrying is safe.
class CalibrationUnavailableError extends SimulationsRepositoryError {
  CalibrationUnavailableError(super.message);
}
