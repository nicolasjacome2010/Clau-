import 'decision_summary.dart';

/// Port over the backend's `decisions` bounded context
/// (backend/src/core_api/decisions/api/router.py).
///
/// `createDecision` requires a `vertical` because the backend does
/// (career/relationships/finance/business/relocation/conflict). Home's
/// free-text input alone can't supply one, so decisions are NOT created
/// from Home directly: the input hands off to Pantalla 5 (Clarificación),
/// whose first chip question resolves the vertical explicitly, and only
/// then is the decision created. That's the spec's own mechanism —
/// docs/UX_DESIGN.md Pantalla 5 is defined as "opciones de respuesta
/// rápida (chips) siempre que sea posible" precisely so the system asks
/// instead of guessing — not an invented workaround.
abstract class DecisionsRepository {
  Future<List<DecisionSummary>> listDecisions();

  /// Returns the created decision's id.
  Future<String> createDecision({
    required String rawInput,
    required String vertical,
  });
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
