import 'dart:convert';

import 'package:dio/dio.dart';

import '../domain/privacy_repository.dart';

/// Real adapter over `GET /v1/privacy/export` and
/// `DELETE /v1/privacy/data`.
class ApiPrivacyRepository implements PrivacyRepository {
  ApiPrivacyRepository(this._dio);

  final Dio _dio;

  @override
  Future<String> exportMyData() async {
    final Response<dynamic> response;
    try {
      response = await _dio.get<dynamic>('/v1/privacy/export');
    } on DioException catch (exc) {
      if (exc.response?.statusCode == 404) {
        throw NothingToExportError('No data to export yet');
      }
      throw PrivacyRepositoryError('Failed to export data: ${exc.message}');
    }

    final data = response.data;
    if (data is! Map) {
      throw PrivacyRepositoryError('Unexpected export response shape');
    }
    // Re-encoded with indentation because a human is about to read this:
    // an export the user can't skim is a worse copy of their own records
    // than one they can.
    return const JsonEncoder.withIndent('  ').convert(data);
  }

  @override
  Future<void> eraseMyData() async {
    try {
      await _dio.delete<dynamic>('/v1/privacy/data');
    } on DioException catch (exc) {
      if (exc.response?.statusCode == 409) {
        throw ActiveSubscriptionError('Subscription still active');
      }
      throw PrivacyRepositoryError('Failed to erase data: ${exc.message}');
    }
  }
}
