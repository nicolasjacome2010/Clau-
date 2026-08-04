import 'decision_summary.dart';

/// Port over the backend's `decisions` bounded context
/// (backend/src/core_api/decisions/api/router.py).
///
/// Only `listDecisions` has a concrete adapter today
/// (`ApiDecisionsRepository`). Home's decision-input field is
/// intentionally NOT wired to `POST /v1/decisions` yet: that endpoint
/// requires a `vertical` (career/relationships/finance/business/
/// relocation/conflict — backend/src/core_api/decisions/domain/
/// entities.py's `DecisionVertical`), and neither docs/UX_DESIGN.md's
/// Pantalla 4 wireframe nor Pantalla 5 (Clarificación) specify where that
/// gets resolved from a single free-text input. Guessing a default
/// vertical would silently mis-classify most decisions in real backend
/// data — a real product decision this module doesn't make unilaterally,
/// same posture `RunSimulationUseCase` takes on the backend when a
/// decision's next state isn't its call to make alone.
abstract class DecisionsRepository {
  Future<List<DecisionSummary>> listDecisions();
}

/// Raised for any failure listing decisions: network error, non-2xx
/// response, or a response that doesn't match the expected shape — mirrors
/// `RealityEngineError` on the backend (one error type per port, never a
/// leaked `DioException`/`http.Response` reaching presentation code).
class DecisionsRepositoryError implements Exception {
  DecisionsRepositoryError(this.message);

  final String message;

  @override
  String toString() => 'DecisionsRepositoryError: $message';
}
