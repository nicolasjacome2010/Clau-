import 'package:dio/dio.dart';

import '../domain/goal.dart';
import '../domain/goals_repository.dart';

/// Real adapter over `GET`/`POST /v1/goals` and `PATCH /v1/goals/{id}`,
/// same conventions as `decisions`' and `memory`'s adapters (defensive
/// parsing, no schema package yet — see `ApiDecisionsRepository`'s
/// docstring for why).
class ApiGoalsRepository implements GoalsRepository {
  ApiGoalsRepository(this._dio);

  final Dio _dio;

  Goal _toGoal(Object? raw) {
    if (raw is! Map) {
      throw GoalsRepositoryError('Unexpected goal entry shape');
    }
    return Goal(
      id: raw['id'] as String,
      name: raw['name'] as String,
      defaultWeight: raw['default_weight'] as int,
      isActive: raw['is_active'] as bool,
    );
  }

  @override
  Future<List<Goal>> listGoals() async {
    final Response<dynamic> response;
    try {
      response = await _dio.get<dynamic>('/v1/goals');
    } on DioException catch (exc) {
      throw GoalsRepositoryError('Failed to load goals: ${exc.message}');
    }

    final data = response.data;
    if (data is! List) {
      throw GoalsRepositoryError('Unexpected /v1/goals response shape');
    }
    return data.map(_toGoal).toList();
  }

  @override
  Future<Goal> createGoal({
    required String name,
    int defaultWeight = 50,
  }) async {
    final Response<dynamic> response;
    try {
      response = await _dio.post<dynamic>(
        '/v1/goals',
        data: {'name': name, 'default_weight': defaultWeight},
      );
    } on DioException catch (exc) {
      throw GoalsRepositoryError('Failed to create goal: ${exc.message}');
    }
    return _toGoal(response.data);
  }

  @override
  Future<Goal> updateGoal({
    required String id,
    int? defaultWeight,
    bool? isActive,
  }) async {
    // Only send what actually changed: the backend's `UpdateGoalRequest`
    // treats every field as optional, and omitting the rest keeps this from
    // clobbering a value another device just changed.
    final payload = <String, Object?>{
      if (defaultWeight != null) 'default_weight': defaultWeight,
      if (isActive != null) 'is_active': isActive,
    };

    final Response<dynamic> response;
    try {
      response = await _dio.patch<dynamic>('/v1/goals/$id', data: payload);
    } on DioException catch (exc) {
      throw GoalsRepositoryError('Failed to update goal: ${exc.message}');
    }
    return _toGoal(response.data);
  }
}
