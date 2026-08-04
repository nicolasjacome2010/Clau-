import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_client.dart';
import '../../data/api_goals_repository.dart';
import '../../domain/goal.dart';
import '../../domain/goals_repository.dart';

final goalsRepositoryProvider = Provider<GoalsRepository>(
  (ref) => ApiGoalsRepository(ref.read(dioProvider)),
);

/// Loads and mutates the user's goals (Pantalla 13).
///
/// Every mutation re-reads the list from the server rather than patching
/// local state optimistically: the backend owns weight normalization and
/// `is_active` filtering (`GET /v1/goals` only returns active goals), so
/// re-fetching is what keeps the screen honest about what's actually
/// stored. These lists are small enough that the extra round trip costs
/// nothing meaningful.
class GoalsController extends AsyncNotifier<List<Goal>> {
  @override
  Future<List<Goal>> build() => _fetch();

  Future<void> refresh() async {
    state = const AsyncLoading<List<Goal>>().copyWithPrevious(state);
    state = await AsyncValue.guard(_fetch);
  }

  Future<void> addGoal(String name) async {
    final trimmed = name.trim();
    if (trimmed.isEmpty) return;
    await _mutate(
      () => ref.read(goalsRepositoryProvider).createGoal(name: trimmed),
    );
  }

  Future<void> setWeight(String id, int weight) async {
    await _mutate(
      () => ref
          .read(goalsRepositoryProvider)
          .updateGoal(id: id, defaultWeight: weight),
    );
  }

  Future<void> removeGoal(String id) async {
    await _mutate(
      () =>
          ref.read(goalsRepositoryProvider).updateGoal(id: id, isActive: false),
    );
  }

  Future<void> _mutate(Future<Goal> Function() operation) async {
    state = const AsyncLoading<List<Goal>>().copyWithPrevious(state);
    state = await AsyncValue.guard(() async {
      await operation();
      return _fetch();
    });
  }

  Future<List<Goal>> _fetch() => ref.read(goalsRepositoryProvider).listGoals();
}

final goalsControllerProvider =
    AsyncNotifierProvider<GoalsController, List<Goal>>(GoalsController.new);
