import 'goal.dart';

/// Port over the backend's `goals` bounded context
/// (backend/src/core_api/goals/api/router.py).
///
/// `listGoals` maps to `GET /v1/goals`, which returns **only active
/// goals** (`ListActiveGoalsUseCase` — there is no `include_inactive`
/// parameter). That shapes the screen: deactivating a goal makes it
/// disappear from the client's view for good, since nothing can list it
/// again to offer re-activation. Perfil de Objetivos therefore labels that
/// action "Quitar" — what the user actually experiences — rather than a
/// reversible-sounding toggle. Re-activation needs a backend change (an
/// `include_inactive` flag on the list endpoint), not a client workaround.
abstract class GoalsRepository {
  Future<List<Goal>> listGoals();

  Future<Goal> createGoal({required String name, int defaultWeight});

  Future<Goal> updateGoal({
    required String id,
    int? defaultWeight,
    bool? isActive,
  });
}

/// Mirrors `DecisionsRepositoryError`/`MemoryRepositoryError`: one error
/// type per port, never a leaked `DioException` reaching presentation code.
class GoalsRepositoryError implements Exception {
  GoalsRepositoryError(this.message);

  final String message;

  @override
  String toString() => 'GoalsRepositoryError: $message';
}
