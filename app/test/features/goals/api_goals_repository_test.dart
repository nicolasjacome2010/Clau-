import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:var_os_app/features/goals/data/api_goals_repository.dart';
import 'package:var_os_app/features/goals/domain/goals_repository.dart';

/// Captures the outgoing request so tests can assert on exactly what would
/// reach the backend, then replays a canned body — no network involved.
class _RecordingAdapter implements HttpClientAdapter {
  _RecordingAdapter(this._body);

  final String _body;
  RequestOptions? lastRequest;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    lastRequest = options;
    return ResponseBody.fromString(
      _body,
      200,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

Dio _dioWith(HttpClientAdapter adapter) {
  final dio = Dio(BaseOptions(baseUrl: 'http://test'));
  dio.httpClientAdapter = adapter;
  return dio;
}

const _goalJson = {
  'id': 'g1',
  'name': 'Estabilidad financiera',
  'default_weight': 70,
  'is_active': true,
  'created_at': '2026-01-01T00:00:00Z',
};

void main() {
  test('parses a well-formed /v1/goals list', () async {
    final repo = ApiGoalsRepository(
      _dioWith(_RecordingAdapter(jsonEncode([_goalJson]))),
    );

    final goals = await repo.listGoals();

    expect(goals, hasLength(1));
    expect(goals.single.id, 'g1');
    expect(goals.single.name, 'Estabilidad financiera');
    expect(goals.single.defaultWeight, 70);
    expect(goals.single.isActive, isTrue);
  });

  test('createGoal posts name and weight', () async {
    final adapter = _RecordingAdapter(jsonEncode(_goalJson));
    final repo = ApiGoalsRepository(_dioWith(adapter));

    await repo.createGoal(name: 'Salud', defaultWeight: 80);

    expect(adapter.lastRequest?.method, 'POST');
    expect(adapter.lastRequest?.path, '/v1/goals');
    expect(adapter.lastRequest?.data, {'name': 'Salud', 'default_weight': 80});
  });

  test('updateGoal only sends the fields that changed', () async {
    final adapter = _RecordingAdapter(jsonEncode(_goalJson));
    final repo = ApiGoalsRepository(_dioWith(adapter));

    await repo.updateGoal(id: 'g1', defaultWeight: 30);

    expect(adapter.lastRequest?.method, 'PATCH');
    expect(adapter.lastRequest?.path, '/v1/goals/g1');
    expect(adapter.lastRequest?.data, {'default_weight': 30});

    await repo.updateGoal(id: 'g1', isActive: false);
    expect(adapter.lastRequest?.data, {'is_active': false});
  });

  test('rejects a non-list response shape', () async {
    final repo = ApiGoalsRepository(
      _dioWith(_RecordingAdapter(jsonEncode({'not': 'a list'}))),
    );

    expect(repo.listGoals(), throwsA(isA<GoalsRepositoryError>()));
  });
}
