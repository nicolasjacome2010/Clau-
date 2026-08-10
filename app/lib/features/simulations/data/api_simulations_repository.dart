import 'dart:convert';

import 'package:dio/dio.dart';

import '../domain/decision_outcome.dart';
import '../domain/simulation.dart';
import '../domain/simulation_progress.dart';
import '../domain/simulations_repository.dart';

/// Real adapter over `GET`/`POST /v1/decisions/{id}/simulations`,
/// `POST /v1/decisions/{id}/outcome` and `GET /v1/outcomes`.
class ApiSimulationsRepository implements SimulationsRepository {
  ApiSimulationsRepository(this._dio);

  final Dio _dio;

  /// Generous relative to the app's 10s default: `POST` blocks for the whole
  /// Reality Engine pipeline (docs/ARCHITECTURE.md §2.2 budgets 15-30s), so
  /// the default connect/receive timeout would abort a perfectly healthy run.
  static const _runTimeout = Duration(seconds: 90);

  Simulation _toSimulation(Object? raw) {
    if (raw is! Map) {
      throw SimulationsRepositoryError('Unexpected simulation shape');
    }

    final safety = raw['safety_gate_result'];
    final safetyMap = safety is Map ? safety : const {};
    final scenarios = raw['scenarios'];
    final completedAt = raw['completed_at'] as String?;

    return Simulation(
      id: raw['id'] as String,
      decisionId: raw['decision_id'] as String,
      status: raw['status'] as String,
      safetyGate: SafetyGateResult(
        // A run that never reached the gate (a transport failure, status
        // `failed`) has an empty result map. Defaulting `safeToProceed` to
        // true keeps that from masquerading as a safety halt — the failure
        // is reported as a failure, not as a crisis referral.
        safeToProceed: safetyMap['safe_to_proceed'] as bool? ?? true,
        recommendedAction: safetyMap['recommended_action'] as String? ?? '',
      ),
      scenarios: scenarios is List
          ? scenarios.map(_toScenario).toList()
          : const [],
      synthesisText: raw['synthesis_text'] as String?,
      reflectiveQuestion: raw['reflective_question'] as String?,
      startedAt: DateTime.parse(raw['started_at'] as String),
      completedAt: completedAt != null ? DateTime.parse(completedAt) : null,
    );
  }

  SimulationScenario _toScenario(Object? raw) {
    if (raw is! Map) {
      throw SimulationsRepositoryError('Unexpected scenario shape');
    }
    final alignments = raw['goal_alignment_scores'];

    return SimulationScenario(
      id: raw['id'] as String,
      title: raw['title'] as String,
      narrative: raw['narrative'] as String,
      assumptions: (raw['assumptions'] as List? ?? const []).cast<String>(),
      relativeProbability: (raw['relative_probability'] as num).toDouble(),
      timeHorizonMonths: raw['time_horizon_months'] as int,
      goalAlignmentScores: alignments is List
          ? alignments.whereType<Map>().map(_toAlignment).toList()
          : const [],
      riskScore: (raw['risk_score'] as num).toDouble(),
      reversibilityScore: (raw['reversibility_score'] as num).toDouble(),
      finalScore: (raw['final_score'] as num).toDouble(),
      rank: raw['rank'] as int,
    );
  }

  GoalAlignment _toAlignment(Map<dynamic, dynamic> raw) {
    return GoalAlignment(
      goal: raw['goal'] as String? ?? '',
      score: (raw['score'] as num? ?? 0).toDouble(),
      justification: raw['justification'] as String? ?? '',
    );
  }

  @override
  Future<List<Simulation>> listForDecision(String decisionId) async {
    final Response<dynamic> response;
    try {
      response = await _dio.get<dynamic>(
        '/v1/decisions/$decisionId/simulations',
      );
    } on DioException catch (exc) {
      throw SimulationsRepositoryError(
        'Failed to load simulations: ${exc.message}',
      );
    }

    final data = response.data;
    if (data is! List) {
      throw SimulationsRepositoryError('Unexpected simulations response shape');
    }
    return data.map(_toSimulation).toList();
  }

  @override
  Future<Simulation> runSimulation(String decisionId) async {
    final Response<dynamic> response;
    try {
      response = await _dio.post<dynamic>(
        '/v1/decisions/$decisionId/simulations',
        options: Options(receiveTimeout: _runTimeout, sendTimeout: _runTimeout),
      );
    } on DioException catch (exc) {
      throw SimulationsRepositoryError(
        'Failed to run simulation: ${exc.message}',
      );
    }
    return _toSimulation(response.data);
  }

  @override
  Stream<SimulationProgressEvent> runSimulationStream(
    String decisionId,
  ) async* {
    final Response<ResponseBody> response;
    try {
      response = await _dio.post<ResponseBody>(
        '/v1/decisions/$decisionId/simulations/stream',
        options: Options(
          responseType: ResponseType.stream,
          receiveTimeout: _runTimeout,
          sendTimeout: _runTimeout,
        ),
      );
    } on DioException catch (exc) {
      // Headers (and, on a 404, the status) arrive before this future
      // resolves even in stream mode — an ownership failure lands here as a
      // real exception, never as a line inside the body.
      throw SimulationsRepositoryError(
        'Failed to start simulation stream: ${exc.message}',
      );
    }

    final lines = response.data!.stream
        .cast<List<int>>()
        .transform(utf8.decoder)
        .transform(const LineSplitter());

    await for (final line in lines) {
      if (line.trim().isEmpty) continue;
      yield _toProgressEvent(line);
    }
  }

  SimulationProgressEvent _toProgressEvent(String line) {
    final Object? decoded;
    try {
      decoded = jsonDecode(line);
    } on FormatException {
      throw SimulationsRepositoryError('Malformed stream line: $line');
    }
    if (decoded is! Map) {
      throw SimulationsRepositoryError('Unexpected stream event shape');
    }

    switch (decoded['type']) {
      case 'stage':
        return SimulationStageProgress(
          stage: decoded['stage'] as String,
          status: decoded['status'] as String,
        );
      case 'result':
        return SimulationProgressResult(_toSimulation(decoded['result']));
      case 'error':
        return SimulationProgressError(
          decoded['message'] as String? ?? 'La simulación no pudo completarse.',
        );
      default:
        throw SimulationsRepositoryError(
          'Unexpected stream event type: ${decoded['type']}',
        );
    }
  }

  @override
  Future<List<DecisionOutcome>> listOutcomes() async {
    final Response<dynamic> response;
    try {
      response = await _dio.get<dynamic>('/v1/outcomes');
    } on DioException catch (exc) {
      throw SimulationsRepositoryError(
        'Failed to load outcomes: ${exc.message}',
      );
    }

    final data = response.data;
    if (data is! List) {
      throw SimulationsRepositoryError('Unexpected outcomes response shape');
    }
    return data.map(_toOutcome).toList();
  }

  @override
  Future<DecisionOutcome> reportOutcome({
    required String decisionId,
    required String reportedOutcome,
  }) async {
    final Response<dynamic> response;
    try {
      response = await _dio.post<dynamic>(
        '/v1/decisions/$decisionId/outcome',
        data: {'reported_outcome': reportedOutcome},
        // Calibration is one more synchronous Reality Engine round trip
        // (Agente 12), so the app-wide default is just as wrong here as it
        // is for `runSimulation` — a single agent, but the same provider.
        options: Options(receiveTimeout: _runTimeout, sendTimeout: _runTimeout),
      );
    } on DioException catch (exc) {
      // Typed per status, so the screen can say something true instead of a
      // generic "algo salió mal". 409 covers two different conflicts and
      // only prose separates them, so it stays deliberately ambiguous here
      // — `DecisionOutcomeController` resolves it against `GET /v1/outcomes`
      // rather than by parsing a message across a service boundary.
      final status = exc.response?.statusCode;
      if (status == 409) {
        throw OutcomeConflictError('Outcome conflict: ${exc.response?.data}');
      }
      if (status == 503) {
        throw CalibrationUnavailableError(
          'Calibration is temporarily unavailable',
        );
      }
      throw SimulationsRepositoryError(
        'Failed to report outcome: ${exc.message}',
      );
    }
    return _toOutcome(response.data);
  }

  DecisionOutcome _toOutcome(Object? raw) {
    if (raw is! Map) {
      throw SimulationsRepositoryError('Unexpected outcome shape');
    }
    final errors = raw['system_errors_identified'];

    return DecisionOutcome(
      id: raw['id'] as String,
      decisionId: raw['decision_id'] as String,
      reportedOutcome: raw['reported_outcome'] as String,
      closestScenarioId: raw['closest_scenario_id'] as String?,
      calibrationDelta: (raw['calibration_delta'] as num? ?? 0).toDouble(),
      systemErrorsIdentified: errors is List
          ? errors.whereType<String>().toList()
          : const [],
      reportedAt: DateTime.parse(raw['reported_at'] as String),
    );
  }
}
