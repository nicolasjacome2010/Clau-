import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Base URL of the Core API. Injected via `--dart-define=API_BASE_URL=...`
/// at build time — never hardcoded per-environment (docs/ARCHITECTURE.md §3).
const String apiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://localhost:8000',
);

/// Reads the current Supabase access token for the auth interceptor.
///
/// Deliberately a plain provider here, not an import of `features/auth`:
/// `core/` must never depend on a feature (layering runs one way — features
/// depend on core). `main.dart` overrides it with `features/auth`'s
/// `sessionControllerProvider`, so the wiring lives at the composition
/// root. Unoverridden — in a widget test, or before any session exists —
/// requests simply carry no `Authorization` header.
final accessTokenProvider = Provider<String?>((ref) => null);

final dioProvider = Provider<Dio>((ref) {
  final dio = Dio(
    BaseOptions(
      baseUrl: apiBaseUrl,
      connectTimeout: const Duration(seconds: 10),
    ),
  );
  dio.interceptors.add(_AuthInterceptor(ref));
  dio.interceptors.add(_StructuredLoggingInterceptor());
  return dio;
});

class _AuthInterceptor extends Interceptor {
  _AuthInterceptor(this._ref);
  final Ref _ref;

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    final token = _ref.read(accessTokenProvider);
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  // There is no refresh-on-401 retry here, and there shouldn't be: the
  // Supabase SDK refreshes the session in the background and pushes the new
  // token through `AuthRepository.accessTokenChanges`, so every request
  // already reads the current one. Re-implementing refresh at this layer
  // would race with the SDK's own, and two components refreshing the same
  // token is how refresh-token reuse detection gets tripped.
}

/// Stand-in for structured logging (backend uses `structlog`,
/// docs/ARCHITECTURE.md §10) until this app wires a real log sink.
class _StructuredLoggingInterceptor extends Interceptor {
  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    debugPrint('[http] -> ${options.method} ${options.path}');
    handler.next(options);
  }

  @override
  void onResponse(
    Response<dynamic> response,
    ResponseInterceptorHandler handler,
  ) {
    debugPrint(
      '[http] <- ${response.statusCode} ${response.requestOptions.path}',
    );
    handler.next(response);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    debugPrint(
      '[http] xx ${err.response?.statusCode} ${err.requestOptions.path}: ${err.message}',
    );
    handler.next(err);
  }
}
