import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:var_os_app/features/privacy/data/api_privacy_repository.dart';
import 'package:var_os_app/features/privacy/domain/privacy_repository.dart';

class _FakeHttpClientAdapter implements HttpClientAdapter {
  _FakeHttpClientAdapter.json(this._body, {int status = 200})
    : _status = status;

  final String _body;
  final int _status;

  final List<RequestOptions> requests = [];

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    requests.add(options);
    return ResponseBody.fromString(
      _body,
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

void main() {
  test('exportMyData returns the document, indented for a human', () async {
    final adapter = _FakeHttpClientAdapter.json(
      jsonEncode({
        'user': {'email': 'alejandro@example.com'},
        'notes': ['algo'],
      }),
    );

    final document = await ApiPrivacyRepository(
      _dioWith(adapter),
    ).exportMyData();

    expect(adapter.requests.single.path, '/v1/privacy/export');
    expect(document, contains('alejandro@example.com'));
    expect(document, contains('\n  '));
    // Round-trips: what the user gets is still machine-readable.
    expect(jsonDecode(document), isA<Map<String, dynamic>>());
  });

  test('exportMyData keeps fields this client knows nothing about', () async {
    // The export is the user's copy of their own records — the app must not
    // drop what it doesn't happen to model.
    final adapter = _FakeHttpClientAdapter.json(
      jsonEncode({
        'user': {},
        'una_seccion_futura': [1, 2, 3],
      }),
    );

    final document = await ApiPrivacyRepository(
      _dioWith(adapter),
    ).exportMyData();

    expect(jsonDecode(document), containsPair('una_seccion_futura', [1, 2, 3]));
  });

  test('maps 404 to NothingToExportError', () async {
    final dio = _dioWith(
      _FakeHttpClientAdapter.json(jsonEncode({'detail': 'none'}), status: 404),
    );

    expect(
      ApiPrivacyRepository(dio).exportMyData(),
      throwsA(isA<NothingToExportError>()),
    );
  });

  test('eraseMyData sends a DELETE', () async {
    final adapter = _FakeHttpClientAdapter.json('', status: 204);

    await ApiPrivacyRepository(_dioWith(adapter)).eraseMyData();

    expect(adapter.requests.single.method, 'DELETE');
    expect(adapter.requests.single.path, '/v1/privacy/data');
  });

  test('maps 409 to ActiveSubscriptionError', () async {
    final dio = _dioWith(
      _FakeHttpClientAdapter.json(
        jsonEncode({'detail': 'cancel first'}),
        status: 409,
      ),
    );

    expect(
      ApiPrivacyRepository(dio).eraseMyData(),
      throwsA(isA<ActiveSubscriptionError>()),
    );
  });

  test('any other failure keeps the base error type', () async {
    final dio = _dioWith(
      _FakeHttpClientAdapter.json(jsonEncode({'detail': 'boom'}), status: 500),
    );

    expect(
      ApiPrivacyRepository(dio).eraseMyData(),
      throwsA(
        allOf(
          isA<PrivacyRepositoryError>(),
          isNot(isA<ActiveSubscriptionError>()),
        ),
      ),
    );
  });
}
