import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:var_os_app/features/decisions/data/api_decisions_repository.dart';
import 'package:var_os_app/features/decisions/domain/decisions_repository.dart';

/// A minimal `HttpClientAdapter` fake, same idea as the backend's
/// `httpx.MockTransport` — no real network, just a canned response/error
/// so this test verifies *our* parsing code, not connectivity.
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
  test('parses a well-formed /v1/decisions response', () async {
    final dio = _dioWith(
      _FakeHttpClientAdapter.json(
        jsonEncode([
          {
            'id': 'd1',
            'title': '¿Debo aceptar?',
            'vertical': 'career',
            'status': 'draft',
            'created_at': '2026-01-01T00:00:00Z',
            'updated_at': '2026-02-01T00:00:00Z',
          },
        ]),
      ),
    );
    final repo = ApiDecisionsRepository(dio);

    final decisions = await repo.listDecisions();

    expect(decisions, hasLength(1));
    expect(decisions.single.id, 'd1');
    expect(decisions.single.title, '¿Debo aceptar?');
    expect(decisions.single.vertical, 'career');
    expect(decisions.single.status, 'draft');
    expect(decisions.single.createdAt, DateTime.parse('2026-01-01T00:00:00Z'));
    expect(decisions.single.updatedAt, DateTime.parse('2026-02-01T00:00:00Z'));
  });

  test('returns an empty list for an empty response', () async {
    final dio = _dioWith(_FakeHttpClientAdapter.json(jsonEncode(<Object?>[])));
    final repo = ApiDecisionsRepository(dio);

    expect(await repo.listDecisions(), isEmpty);
  });

  test('wraps a network failure in DecisionsRepositoryError', () async {
    final dio = _dioWith(
      _FakeHttpClientAdapter.throwing(
        DioException(
          requestOptions: RequestOptions(path: '/v1/decisions'),
          message: 'boom',
        ),
      ),
    );
    final repo = ApiDecisionsRepository(dio);

    expect(repo.listDecisions(), throwsA(isA<DecisionsRepositoryError>()));
  });

  test('rejects a non-list response shape', () async {
    final dio = _dioWith(
      _FakeHttpClientAdapter.json(jsonEncode({'not': 'a list'})),
    );
    final repo = ApiDecisionsRepository(dio);

    expect(repo.listDecisions(), throwsA(isA<DecisionsRepositoryError>()));
  });
}
