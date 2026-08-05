import 'dart:async';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:var_os_app/core/network/api_client.dart';
import 'package:var_os_app/features/auth/domain/auth_repository.dart';
import 'package:var_os_app/features/auth/presentation/controllers/session_controller.dart';

class _FakeAuthRepository implements AuthRepository {
  _FakeAuthRepository({this.initialToken});

  final String? initialToken;
  final StreamController<String?> _tokens =
      StreamController<String?>.broadcast();

  @override
  String? get currentAccessToken => initialToken;

  @override
  Stream<String?> get accessTokenChanges => _tokens.stream;

  void emit(String? token) => _tokens.add(token);

  @override
  Future<void> signInWithEmail(String email) async {}

  @override
  Future<void> continueAnonymously() async {}
}

/// Records the headers of whatever request reaches the transport, so the
/// test can assert on what the Core API would actually receive.
class _HeaderSpyAdapter implements HttpClientAdapter {
  Map<String, dynamic> lastHeaders = const {};

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    lastHeaders = options.headers;
    return ResponseBody.fromString('{}', 200);
  }

  @override
  void close({bool force = false}) {}
}

ProviderContainer _containerWith(AuthRepository repository) {
  final container = ProviderContainer(
    overrides: [
      authRepositoryProvider.overrideWithValue(repository),
      // Exactly what `main.dart` does at the composition root.
      accessTokenProvider.overrideWith(
        (ref) => ref.watch(sessionControllerProvider),
      ),
    ],
  );
  addTearDown(container.dispose);
  return container;
}

void main() {
  test('starts from the session the SDK already restored', () {
    final container = _containerWith(
      _FakeAuthRepository(initialToken: 'restored'),
    );

    expect(container.read(sessionControllerProvider), 'restored');
  });

  test('follows sign-in, refresh and sign-out', () async {
    final repository = _FakeAuthRepository();
    final container = _containerWith(repository);
    // Listened so the notifier stays alive between emissions.
    container.listen(sessionControllerProvider, (_, _) {});

    expect(container.read(sessionControllerProvider), isNull);

    repository.emit('first');
    await Future<void>.delayed(Duration.zero);
    expect(container.read(sessionControllerProvider), 'first');

    // A silent refresh from the SDK — the app follows it rather than
    // refreshing anything itself.
    repository.emit('refreshed');
    await Future<void>.delayed(Duration.zero);
    expect(container.read(sessionControllerProvider), 'refreshed');

    repository.emit(null);
    await Future<void>.delayed(Duration.zero);
    expect(container.read(sessionControllerProvider), isNull);
  });

  test('the token reaches the Core API as a bearer header', () async {
    final container = _containerWith(
      _FakeAuthRepository(initialToken: 'jwt-1'),
    );
    final adapter = _HeaderSpyAdapter();
    final dio = container.read(dioProvider)..httpClientAdapter = adapter;

    await dio.get<dynamic>('/v1/decisions');

    expect(adapter.lastHeaders['Authorization'], 'Bearer jwt-1');
  });

  test('no session means no Authorization header at all', () async {
    // Not an empty one: an unauthenticated request that gets a truthful 401
    // beats one carrying a token no server accepts.
    final container = _containerWith(_FakeAuthRepository());
    final adapter = _HeaderSpyAdapter();
    final dio = container.read(dioProvider)..httpClientAdapter = adapter;

    await dio.get<dynamic>('/v1/decisions');

    expect(adapter.lastHeaders.containsKey('Authorization'), isFalse);
  });
}
