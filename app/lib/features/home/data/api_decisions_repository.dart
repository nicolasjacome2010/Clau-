import 'package:dio/dio.dart';

import '../domain/decision_summary.dart';
import '../domain/decisions_repository.dart';

/// Real adapter over `GET /v1/decisions`. Uses the shared `Dio` instance
/// from `core/network/api_client.dart`, so it automatically carries
/// whatever `Authorization` header `features/auth` has set — there is
/// nothing decisions-specific about auth here.
///
/// Parses the response defensively (`is Map`/`is List` checks) rather than
/// trusting the shape, because unlike the backend's own `RealityEngineClient`
/// (which validates against Pydantic models), this app doesn't have an
/// equivalent typed-parsing layer yet — a deliberate scope cut for this
/// increment, not an oversight: this is the only endpoint this app calls
/// today, so a full schema-validation package isn't earning its keep yet.
class ApiDecisionsRepository implements DecisionsRepository {
  ApiDecisionsRepository(this._dio);

  final Dio _dio;

  @override
  Future<List<DecisionSummary>> listDecisions() async {
    final Response<dynamic> response;
    try {
      response = await _dio.get<dynamic>('/v1/decisions');
    } on DioException catch (exc) {
      throw DecisionsRepositoryError(
        'Failed to load decisions: ${exc.message}',
      );
    }

    final data = response.data;
    if (data is! List) {
      throw DecisionsRepositoryError('Unexpected /v1/decisions response shape');
    }

    return data.map((raw) {
      if (raw is! Map) {
        throw DecisionsRepositoryError('Unexpected decision entry shape');
      }
      return DecisionSummary(
        id: raw['id'] as String,
        title: raw['title'] as String,
        vertical: raw['vertical'] as String,
        status: raw['status'] as String,
      );
    }).toList();
  }
}
