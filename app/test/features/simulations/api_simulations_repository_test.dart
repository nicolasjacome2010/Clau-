import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:var_os_app/features/simulations/data/api_simulations_repository.dart';
import 'package:var_os_app/features/simulations/domain/simulation_progress.dart';
import 'package:var_os_app/features/simulations/domain/simulations_repository.dart';

/// Same `httpx.MockTransport` equivalent the other repository tests use: no
/// real network, so this exercises our parsing, not connectivity.
class _FakeHttpClientAdapter implements HttpClientAdapter {
  _FakeHttpClientAdapter.json(this._body, {int status = 200})
    : _throws = null,
      _status = status;
  _FakeHttpClientAdapter.ndjson(List<String> lines, {int status = 200})
    : _body = lines.map((line) => '$line\n').join(),
      _throws = null,
      _status = status;
  _FakeHttpClientAdapter.throwing(Object error)
    : _body = null,
      _throws = error,
      _status = 200;

  final String? _body;
  final Object? _throws;
  final int _status;

  /// The options of every request that reached the adapter, so a test can
  /// assert on what was actually sent (the long run timeout, notably).
  final List<RequestOptions> requests = [];

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    requests.add(options);
    if (_throws != null) throw _throws;
    return ResponseBody.fromString(
      _body!,
      _status,
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

Map<String, Object?> _simulationJson({
  Map<String, Object?>? safetyGate,
  List<Object?>? scenarios,
  String status = 'completed',
}) {
  return {
    'id': 'sim-1',
    'decision_id': 'd1',
    'status': status,
    'safety_gate_result':
        safetyGate ??
        {'safe_to_proceed': true, 'recommended_action': 'proceed'},
    'scenarios': scenarios ?? <Object?>[],
    'synthesis_text': 'Ambos caminos son viables.',
    'reflective_question': '¿Qué te importa más?',
    'started_at': '2026-01-01T00:00:00Z',
    'completed_at': '2026-01-01T00:00:30Z',
  };
}

Map<String, Object?> _scenarioJson() {
  return {
    'id': 's1',
    'title': 'Aceptar la oferta',
    'narrative': 'Te mudás y el equipo crece.',
    'assumptions': ['El equipo se mantiene estable'],
    'relative_probability': 45.5,
    'time_horizon_months': 12,
    'goal_alignment_scores': [
      {
        'goal': 'Estabilidad financiera',
        'score': 80,
        'justification': 'Sueldo mayor',
      },
    ],
    'risk_score': 30,
    'reversibility_score': 70,
    'final_score': 64.2,
    'rank': 1,
  };
}

void main() {
  test('parses a well-formed simulations list', () async {
    final dio = _dioWith(
      _FakeHttpClientAdapter.json(
        jsonEncode([
          _simulationJson(scenarios: [_scenarioJson()]),
        ]),
      ),
    );

    final simulations = await ApiSimulationsRepository(
      dio,
    ).listForDecision('d1');

    expect(simulations, hasLength(1));
    final simulation = simulations.single;
    expect(simulation.id, 'sim-1');
    expect(simulation.decisionId, 'd1');
    expect(simulation.isCompleted, isTrue);
    expect(simulation.safetyGate.requiresReferral, isFalse);
    expect(simulation.synthesisText, 'Ambos caminos son viables.');
    expect(simulation.completedAt, DateTime.parse('2026-01-01T00:00:30Z'));

    final scenario = simulation.scenarios.single;
    expect(scenario.title, 'Aceptar la oferta');
    expect(scenario.assumptions, ['El equipo se mantiene estable']);
    expect(scenario.relativeProbability, 45.5);
    expect(scenario.riskScore, 30);
    expect(scenario.isTopRanked, isTrue);
    expect(scenario.goalAlignmentScores.single.goal, 'Estabilidad financiera');
    expect(scenario.goalAlignmentScores.single.score, 80);
  });

  test('reads a halt out of the safety gate result', () async {
    final dio = _dioWith(
      _FakeHttpClientAdapter.json(
        jsonEncode([
          _simulationJson(
            safetyGate: {
              'safe_to_proceed': false,
              'recommended_action': 'halt_and_refer',
            },
          ),
        ]),
      ),
    );

    final simulations = await ApiSimulationsRepository(
      dio,
    ).listForDecision('d1');

    expect(simulations.single.safetyGate.requiresReferral, isTrue);
  });

  test('an absent safety gate result is not read as a halt', () async {
    // A run that failed before reaching Agente 0 carries an empty map. That
    // is a failure, not a crisis — misreporting it would show a referral to
    // someone who only hit a network error.
    final dio = _dioWith(
      _FakeHttpClientAdapter.json(
        jsonEncode([_simulationJson(safetyGate: const {}, status: 'failed')]),
      ),
    );

    final simulations = await ApiSimulationsRepository(
      dio,
    ).listForDecision('d1');

    expect(simulations.single.safetyGate.requiresReferral, isFalse);
    expect(simulations.single.isFailed, isTrue);
  });

  test('runSimulation posts and parses the returned simulation', () async {
    final adapter = _FakeHttpClientAdapter.json(
      jsonEncode(_simulationJson(scenarios: [_scenarioJson()])),
    );
    final dio = _dioWith(adapter);

    final simulation = await ApiSimulationsRepository(dio).runSimulation('d1');

    expect(simulation.id, 'sim-1');
    expect(simulation.scenarios, hasLength(1));
    expect(adapter.requests.single.method, 'POST');
    expect(adapter.requests.single.path, '/v1/decisions/d1/simulations');
  });

  test('runSimulation allows far longer than the default timeout', () async {
    // Regression guard: the app-wide 10s default would abort a healthy
    // 15-30s pipeline run.
    final adapter = _FakeHttpClientAdapter.json(jsonEncode(_simulationJson()));
    final dio = _dioWith(adapter);

    await ApiSimulationsRepository(dio).runSimulation('d1');

    expect(
      adapter.requests.single.receiveTimeout,
      greaterThanOrEqualTo(const Duration(seconds: 60)),
    );
  });

  test('wraps a network failure in SimulationsRepositoryError', () async {
    final dio = _dioWith(
      _FakeHttpClientAdapter.throwing(
        DioException(
          requestOptions: RequestOptions(path: '/v1/decisions/d1/simulations'),
          message: 'boom',
        ),
      ),
    );

    expect(
      ApiSimulationsRepository(dio).listForDecision('d1'),
      throwsA(isA<SimulationsRepositoryError>()),
    );
  });

  test('reportOutcome posts the text and parses the calibration', () async {
    final adapter = _FakeHttpClientAdapter.json(
      jsonEncode({
        'id': 'o1',
        'decision_id': 'd1',
        'reported_outcome': 'Acepté la oferta.',
        'closest_scenario_id': 's1',
        'calibration_delta': 24.5,
        'system_errors_identified': ['Subestimamos el tiempo de adaptación'],
        'reported_at': '2026-07-01T00:00:00Z',
      }),
    );
    final dio = _dioWith(adapter);

    final outcome = await ApiSimulationsRepository(
      dio,
    ).reportOutcome(decisionId: 'd1', reportedOutcome: 'Acepté la oferta.');

    expect(outcome.id, 'o1');
    expect(outcome.closestScenarioId, 's1');
    expect(outcome.matchedNoScenario, isFalse);
    expect(outcome.calibrationDelta, 24.5);
    expect(outcome.systemErrorsIdentified, [
      'Subestimamos el tiempo de adaptación',
    ]);
    expect(adapter.requests.single.method, 'POST');
    expect(adapter.requests.single.path, '/v1/decisions/d1/outcome');
    expect(adapter.requests.single.data, {
      'reported_outcome': 'Acepté la oferta.',
    });
  });

  test('reportOutcome keeps a null closest scenario as a blind spot', () async {
    final dio = _dioWith(
      _FakeHttpClientAdapter.json(
        jsonEncode({
          'id': 'o1',
          'decision_id': 'd1',
          'reported_outcome': 'Pasó otra cosa.',
          'closest_scenario_id': null,
          'calibration_delta': -10,
          'system_errors_identified': <String>[],
          'reported_at': '2026-07-01T00:00:00Z',
        }),
      ),
    );

    final outcome = await ApiSimulationsRepository(
      dio,
    ).reportOutcome(decisionId: 'd1', reportedOutcome: 'Pasó otra cosa.');

    expect(outcome.matchedNoScenario, isTrue);
  });

  test('maps 409 to the ambiguous-conflict type', () async {
    final dio = _dioWith(
      _FakeHttpClientAdapter.json(jsonEncode({'detail': 'nope'}), status: 409),
    );

    expect(
      ApiSimulationsRepository(
        dio,
      ).reportOutcome(decisionId: 'd1', reportedOutcome: 'algo'),
      throwsA(isA<OutcomeConflictError>()),
    );
  });

  test('maps 503 to CalibrationUnavailableError', () async {
    final dio = _dioWith(
      _FakeHttpClientAdapter.json(jsonEncode({'detail': 'down'}), status: 503),
    );

    expect(
      ApiSimulationsRepository(
        dio,
      ).reportOutcome(decisionId: 'd1', reportedOutcome: 'algo'),
      throwsA(isA<CalibrationUnavailableError>()),
    );
  });

  test('maps any other outcome failure to the base error type', () async {
    final dio = _dioWith(
      _FakeHttpClientAdapter.json(jsonEncode({'detail': 'boom'}), status: 500),
    );

    expect(
      ApiSimulationsRepository(
        dio,
      ).reportOutcome(decisionId: 'd1', reportedOutcome: 'algo'),
      throwsA(
        allOf(
          isA<SimulationsRepositoryError>(),
          isNot(isA<OutcomeConflictError>()),
          isNot(isA<CalibrationUnavailableError>()),
        ),
      ),
    );
  });

  test('rejects a non-list response shape', () async {
    final dio = _dioWith(
      _FakeHttpClientAdapter.json(jsonEncode({'not': 'a list'})),
    );

    expect(
      ApiSimulationsRepository(dio).listForDecision('d1'),
      throwsA(isA<SimulationsRepositoryError>()),
    );
  });

  test('listOutcomes parses the collection', () async {
    final adapter = _FakeHttpClientAdapter.json(
      jsonEncode([
        {
          'id': 'o1',
          'decision_id': 'd1',
          'reported_outcome': 'Acepté la oferta.',
          'closest_scenario_id': null,
          'calibration_delta': -8,
          'system_errors_identified': <String>[],
          'reported_at': '2026-07-01T00:00:00Z',
        },
      ]),
    );
    final dio = _dioWith(adapter);

    final outcomes = await ApiSimulationsRepository(dio).listOutcomes();

    expect(outcomes, hasLength(1));
    expect(outcomes.single.decisionId, 'd1');
    expect(outcomes.single.matchedNoScenario, isTrue);
    expect(adapter.requests.single.method, 'GET');
    expect(adapter.requests.single.path, '/v1/outcomes');
  });

  test('listOutcomes returns an empty list for an empty response', () async {
    final dio = _dioWith(_FakeHttpClientAdapter.json(jsonEncode(<Object?>[])));

    expect(await ApiSimulationsRepository(dio).listOutcomes(), isEmpty);
  });

  test('listOutcomes rejects a non-list response shape', () async {
    final dio = _dioWith(
      _FakeHttpClientAdapter.json(jsonEncode({'not': 'a list'})),
    );

    expect(
      ApiSimulationsRepository(dio).listOutcomes(),
      throwsA(isA<SimulationsRepositoryError>()),
    );
  });

  test(
    'runSimulationStream relays stage events in order, then the result',
    () async {
      final adapter = _FakeHttpClientAdapter.ndjson([
        jsonEncode({
          'type': 'stage',
          'stage': 'safety_gate',
          'status': 'started',
        }),
        jsonEncode({
          'type': 'stage',
          'stage': 'safety_gate',
          'status': 'completed',
        }),
        jsonEncode({'type': 'result', 'result': _simulationJson()}),
      ]);
      final dio = _dioWith(adapter);

      final events = await ApiSimulationsRepository(
        dio,
      ).runSimulationStream('d1').toList();

      expect(events, hasLength(3));
      final first = events[0] as SimulationStageProgress;
      expect(first.stage, 'safety_gate');
      expect(first.status, 'started');
      final last = events[2] as SimulationProgressResult;
      expect(last.simulation.id, 'sim-1');
      expect(
        adapter.requests.single.path,
        '/v1/decisions/d1/simulations/stream',
      );
    },
  );

  test('runSimulationStream surfaces an in-band error line', () async {
    final dio = _dioWith(
      _FakeHttpClientAdapter.ndjson([
        jsonEncode({
          'type': 'stage',
          'stage': 'safety_gate',
          'status': 'started',
        }),
        jsonEncode({
          'type': 'error',
          'message': 'La simulación no pudo completarse.',
        }),
      ]),
    );

    final events = await ApiSimulationsRepository(
      dio,
    ).runSimulationStream('d1').toList();

    expect(events, hasLength(2));
    final error = events[1] as SimulationProgressError;
    expect(error.message, 'La simulación no pudo completarse.');
  });

  test(
    'runSimulationStream wraps an ownership 404 before any event, never as a line',
    () async {
      final dio = _dioWith(
        _FakeHttpClientAdapter.json(
          jsonEncode({'detail': 'Decision not found'}),
          status: 404,
        ),
      );

      expect(
        ApiSimulationsRepository(dio).runSimulationStream('d1').toList(),
        throwsA(isA<SimulationsRepositoryError>()),
      );
    },
  );

  test(
    'runSimulationStream sends the same long timeout as runSimulation',
    () async {
      final adapter = _FakeHttpClientAdapter.ndjson([
        jsonEncode({'type': 'result', 'result': _simulationJson()}),
      ]);
      final dio = _dioWith(adapter);

      await ApiSimulationsRepository(dio).runSimulationStream('d1').toList();

      expect(
        adapter.requests.single.receiveTimeout,
        greaterThanOrEqualTo(const Duration(seconds: 60)),
      );
    },
  );
}
