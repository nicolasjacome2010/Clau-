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
/// depend on core). `features/auth`'s session controller overrides this
/// provider once a real session exists; until then requests simply carry no
/// `Authorization` header, which is correct for the pre-auth "probar antes
/// de registrarse" flow (docs/UX_DESIGN.md, Pantalla 3).
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

  // Automatic refresh-on-401 is intentionally not implemented yet: it
  // depends on `features/auth` wiring a real Supabase session (refresh
  // token, expiry), which this first increment doesn't have. Documented
  // gap, not an oversight — same posture as `simulations/infrastructure/
  // reality_engine_client.py`'s "no queue yet" docstring on the backend.
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
