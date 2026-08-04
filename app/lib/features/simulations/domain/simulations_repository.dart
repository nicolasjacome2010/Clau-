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
abstract class SimulationsRepository {
  Future<List<Simulation>> listForDecision(String decisionId);

  Future<Simulation> runSimulation(String decisionId);
}

/// Mirrors the other ports' error type: never a leaked `DioException`.
class SimulationsRepositoryError implements Exception {
  SimulationsRepositoryError(this.message);

  final String message;

  @override
  String toString() => 'SimulationsRepositoryError: $message';
}
