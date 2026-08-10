import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:var_os_app/features/memory/data/api_memory_repository.dart';
import 'package:var_os_app/features/memory/domain/memory_repository.dart';

class _FakeHttpClientAdapter implements HttpClientAdapter {
  _FakeHttpClientAdapter.json(this._body) : _throws = null;
  _FakeHttpClientAdapter.throwing(Object error) : _body = null, _throws = error;

  final String? _body;
  final Object? _throws;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    if (_throws != null) throw _throws;
    return ResponseBody.fromString(
      _body!,
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

void main() {
  test('parses a well-formed /v1/memory/bias-profile response', () async {
    final dio = _dioWith(
      _FakeHttpClientAdapter.json(
        jsonEncode({
          'biases': [
            {'bias': 'Aversión a la pérdida', 'score': 0.8, 'occurrences': 2},
          ],
          'calibration_score': 12.5,
          'updated_at': '2026-03-01T00:00:00Z',
        }),
      ),
    );
    final repo = ApiMemoryRepository(dio);

    final profile = await repo.getBiasProfile();

    expect(profile.biases, hasLength(1));
    expect(profile.biases.single.bias, 'Aversión a la pérdida');
    expect(profile.biases.single.score, 0.8);
    expect(profile.biases.single.occurrences, 2);
    expect(profile.calibrationScore, 12.5);
    expect(profile.updatedAt, DateTime.parse('2026-03-01T00:00:00Z'));
  });

  test('parses a profile with no biases and a null updated_at', () async {
    final dio = _dioWith(
      _FakeHttpClientAdapter.json(
        jsonEncode({
          'biases': <Object?>[],
          'calibration_score': 0.0,
          'updated_at': null,
        }),
      ),
    );
    final repo = ApiMemoryRepository(dio);

    final profile = await repo.getBiasProfile();

    expect(profile.biases, isEmpty);
    expect(profile.updatedAt, isNull);
  });

  test('wraps a network failure in MemoryRepositoryError', () async {
    final dio = _dioWith(
      _FakeHttpClientAdapter.throwing(
        DioException(
          requestOptions: RequestOptions(path: '/v1/memory/bias-profile'),
          message: 'boom',
        ),
      ),
    );
    final repo = ApiMemoryRepository(dio);

    expect(repo.getBiasProfile(), throwsA(isA<MemoryRepositoryError>()));
  });

  test('rejects a non-map response shape', () async {
    final dio = _dioWith(_FakeHttpClientAdapter.json(jsonEncode(<Object?>[])));
    final repo = ApiMemoryRepository(dio);

    expect(repo.getBiasProfile(), throwsA(isA<MemoryRepositoryError>()));
  });
}
