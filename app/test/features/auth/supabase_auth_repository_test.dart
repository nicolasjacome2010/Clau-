import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:var_os_app/features/auth/data/supabase_auth_repository.dart';

/// Canned HTTP responses, keyed by the path suffix Supabase's auth client
/// hits. Same posture as every other real adapter in this repo: the
/// production class is exercised against a fake transport, never the
/// network — there are no Supabase credentials in CI.
class _FakeAuthServer extends http.BaseClient {
  _FakeAuthServer({this.status = 200, this.body = '{}'});

  final int status;
  final String body;

  /// Every request that reached the transport, so a test can assert on what
  /// would actually be sent to Supabase.
  final List<http.BaseRequest> requests = [];

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    requests.add(request);
    return http.StreamedResponse(
      Stream.value(utf8.encode(body)),
      status,
      request: request,
      headers: {'content-type': 'application/json'},
    );
  }
}

String _sessionJson({String accessToken = 'token-123'}) {
  return jsonEncode({
    'access_token': accessToken,
    'token_type': 'bearer',
    'expires_in': 3600,
    'refresh_token': 'refresh-123',
    'user': {
      'id': '00000000-0000-0000-0000-000000000001',
      'aud': 'authenticated',
      'role': 'authenticated',
      'is_anonymous': true,
      'app_metadata': <String, Object?>{},
      'user_metadata': <String, Object?>{},
      'created_at': '2026-01-01T00:00:00Z',
    },
  });
}

/// The PKCE flow needs somewhere to keep its code verifier between the
/// magic-link request and the redirect back. In production
/// `Supabase.initialize` supplies a persistent one; a test only needs it to
/// exist.
class _MemoryStorage extends GotrueAsyncStorage {
  final Map<String, String> _values = {};

  @override
  Future<String?> getItem({required String key}) async => _values[key];

  @override
  Future<void> setItem({required String key, required String value}) async {
    _values[key] = value;
  }

  @override
  Future<void> removeItem({required String key}) async {
    _values.remove(key);
  }
}

SupabaseClient _clientWith(_FakeAuthServer server) {
  return SupabaseClient(
    'https://project.supabase.co',
    'publishable-key',
    httpClient: server,
    authOptions: AuthClientOptions(
      // Off so a test never leaves a timer running past its own end.
      autoRefreshToken: false,
      pkceAsyncStorage: _MemoryStorage(),
    ),
  );
}

void main() {
  test('signInWithEmail asks Supabase for a magic link', () async {
    final server = _FakeAuthServer();
    final repository = SupabaseAuthRepository(_clientWith(server));

    await repository.signInWithEmail('alejandro@example.com');

    expect(server.requests, hasLength(1));
    expect(server.requests.single.method, 'POST');
    expect(server.requests.single.url.path, contains('/auth/v1/otp'));
  });

  test('signInWithEmail trims before sending', () async {
    final server = _FakeAuthServer();
    final repository = SupabaseAuthRepository(_clientWith(server));

    await repository.signInWithEmail('  alejandro@example.com  ');

    final body = await http.ByteStream(
      Stream.value((server.requests.single as http.Request).bodyBytes),
    ).bytesToString();
    expect(jsonDecode(body), containsPair('email', 'alejandro@example.com'));
  });

  test('an invalid email never reaches the network', () async {
    // The same guard the stub had: a local, free check has no reason to
    // cost a round trip (and a rejected one reads worse to the user).
    final server = _FakeAuthServer();
    final repository = SupabaseAuthRepository(_clientWith(server));

    expect(
      () => repository.signInWithEmail('no-arroba'),
      throwsA(isA<ArgumentError>()),
    );
    expect(server.requests, isEmpty);
  });

  test('continueAnonymously creates a real Supabase session', () async {
    // docs/UX_DESIGN.md Pantalla 3's "probar sin cuenta" must produce a
    // genuine JWT — the Core API's JIT provisioning has nothing to work
    // with otherwise.
    final server = _FakeAuthServer(body: _sessionJson());
    final repository = SupabaseAuthRepository(_clientWith(server));

    await repository.continueAnonymously();

    expect(server.requests.single.url.path, contains('/auth/v1/signup'));
    expect(repository.currentAccessToken, 'token-123');
  });

  test('currentAccessToken is null before any session exists', () {
    final repository = SupabaseAuthRepository(_clientWith(_FakeAuthServer()));

    expect(repository.currentAccessToken, isNull);
  });

  test('accessTokenChanges emits the token of a new session', () async {
    final server = _FakeAuthServer(body: _sessionJson(accessToken: 'fresh'));
    final repository = SupabaseAuthRepository(_clientWith(server));
    final tokens = <String?>[];
    final subscription = repository.accessTokenChanges.listen(tokens.add);

    await repository.continueAnonymously();
    await Future<void>.delayed(Duration.zero);
    await subscription.cancel();

    expect(tokens, contains('fresh'));
  });

  test('a rejected sign-in surfaces the Supabase error', () async {
    final server = _FakeAuthServer(
      status: 400,
      body: jsonEncode({'error_code': 'validation_failed', 'msg': 'nope'}),
    );
    final repository = SupabaseAuthRepository(_clientWith(server));

    expect(
      repository.signInWithEmail('alejandro@example.com'),
      throwsA(isA<AuthException>()),
    );
  });
}
