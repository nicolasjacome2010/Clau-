import 'package:dio/dio.dart';

import '../domain/simulation.dart';
import '../domain/simulations_repository.dart';

/// Real adapter over `GET`/`POST /v1/decisions/{id}/simulations`.
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
}
