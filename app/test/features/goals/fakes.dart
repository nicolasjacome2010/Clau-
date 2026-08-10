import 'package:var_os_app/features/goals/domain/goal.dart';
import 'package:var_os_app/features/goals/domain/goals_repository.dart';

class FakeGoalsRepository implements GoalsRepository {
  FakeGoalsRepository({List<Goal>? goals, this.error, this.failCreateAfter})
    : _goals = [...?goals];

  final List<Goal> _goals;
  final GoalsRepositoryError? error;

  /// Lets `createGoal` succeed this many times, then fail every call after
  /// — how a test reproduces a backend that dies part-way through a batch.
  final int? failCreateAfter;

  final List<({String name, int weight})> createCalls = [];
  final List<({String id, int? weight, bool? isActive})> updateCalls = [];

  @override
  Future<List<Goal>> listGoals() async {
    if (error != null) throw error!;
    // Mirrors `GET /v1/goals`, which only ever returns active goals.
    return _goals.where((goal) => goal.isActive).toList();
  }

  @override
  Future<Goal> createGoal({
    required String name,
    int defaultWeight = 50,
  }) async {
    if (failCreateAfter != null && createCalls.length >= failCreateAfter!) {
      throw GoalsRepositoryError('create failed');
    }
    createCalls.add((name: name, weight: defaultWeight));
    final created = Goal(
      id: 'goal-${_goals.length + 1}',
      name: name,
      defaultWeight: defaultWeight,
      isActive: true,
    );
    _goals.add(created);
    return created;
  }

  @override
  Future<Goal> updateGoal({
    required String id,
    int? defaultWeight,
    bool? isActive,
  }) async {
    updateCalls.add((id: id, weight: defaultWeight, isActive: isActive));
    final index = _goals.indexWhere((goal) => goal.id == id);
    final existing = _goals[index];
    final updated = Goal(
      id: existing.id,
      name: existing.name,
      defaultWeight: defaultWeight ?? existing.defaultWeight,
      isActive: isActive ?? existing.isActive,
    );
    _goals[index] = updated;
    return updated;
  }
}

Goal testGoal({
  required String id,
  required String name,
  int defaultWeight = 50,
  bool isActive = true,
}) {
  return Goal(
    id: id,
    name: name,
    defaultWeight: defaultWeight,
    isActive: isActive,
  );
}
