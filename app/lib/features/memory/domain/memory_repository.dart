import 'user_bias_profile.dart';

/// Port over the backend's `memory` bounded context
/// (backend/src/core_api/memory/api/router.py).
///
/// Only `getBiasProfile` has a concrete adapter today. The backend has no
/// `POST /v1/memory/bias-observations` caller on this app's side (that's
/// written by Reality Engine's Agent 5/12, never by the client), and no
/// export/delete-all-my-data endpoint exists on the backend at all yet —
/// docs/UX_DESIGN.md Pantalla 12 calls for visible "Exportar"/"Borrar"
/// buttons, but wiring them needs a backend endpoint this module doesn't
/// have to invent. See `MemoryTabContent`'s docstring.
abstract class MemoryRepository {
  Future<UserBiasProfile> getBiasProfile();
}

/// Mirrors `DecisionsRepositoryError`/`RealityEngineError`: one error type
/// per port, never a leaked `DioException` reaching presentation code.
class MemoryRepositoryError implements Exception {
  MemoryRepositoryError(this.message);

  final String message;

  @override
  String toString() => 'MemoryRepositoryError: $message';
}
