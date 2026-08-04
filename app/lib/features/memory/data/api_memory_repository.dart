import 'package:dio/dio.dart';

import '../domain/memory_repository.dart';
import '../domain/user_bias_profile.dart';

/// Real adapter over `GET /v1/memory/bias-profile`, same shape/conventions
/// as `decisions`' `ApiDecisionsRepository` (defensive parsing, no schema
/// package yet — see that class's docstring for why).
class ApiMemoryRepository implements MemoryRepository {
  ApiMemoryRepository(this._dio);

  final Dio _dio;

  @override
  Future<UserBiasProfile> getBiasProfile() async {
    final Response<dynamic> response;
    try {
      response = await _dio.get<dynamic>('/v1/memory/bias-profile');
    } on DioException catch (exc) {
      throw MemoryRepositoryError(
        'Failed to load bias profile: ${exc.message}',
      );
    }

    final data = response.data;
    if (data is! Map) {
      throw MemoryRepositoryError(
        'Unexpected /v1/memory/bias-profile response shape',
      );
    }

    final rawBiases = data['biases'];
    if (rawBiases is! List) {
      throw MemoryRepositoryError('Unexpected biases shape');
    }

    final biases = rawBiases.map((raw) {
      if (raw is! Map) {
        throw MemoryRepositoryError('Unexpected bias entry shape');
      }
      return BiasObservation(
        bias: raw['bias'] as String,
        score: (raw['score'] as num).toDouble(),
        occurrences: raw['occurrences'] as int,
      );
    }).toList();

    final updatedAtRaw = data['updated_at'] as String?;
    return UserBiasProfile(
      biases: biases,
      calibrationScore: (data['calibration_score'] as num).toDouble(),
      updatedAt: updatedAtRaw != null ? DateTime.parse(updatedAtRaw) : null,
    );
  }
}
