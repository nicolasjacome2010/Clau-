import 'package:supabase_flutter/supabase_flutter.dart';

import '../domain/auth_repository.dart';

/// The real adapter over Supabase Auth.
///
/// Takes a `SupabaseClient` rather than reaching for `Supabase.instance`
/// itself: that keeps this class constructible in a test against a fake
/// `http.Client`, which is how the repo tests every real adapter (see
/// `test_openai_provider.py` on the Reality Engine side, and the fake
/// `HttpClientAdapter` used for the Dio repositories). There are no
/// Supabase credentials in CI, so this is tested against canned HTTP
/// responses and never the network.
///
/// Only the two sign-in paths docs/UX_DESIGN.md Pantalla 3 offers are
/// implemented — magic link and anonymous. OAuth buttons are in the
/// wireframe but need per-platform redirect URLs (deep links, an iOS URL
/// scheme, an Android intent filter) that this project has no bundle
/// identifiers for yet; adding a method here that can't be reached from a
/// working screen would be worse than its absence.
class SupabaseAuthRepository implements AuthRepository {
  SupabaseAuthRepository(this._client);

  final SupabaseClient _client;

  @override
  Future<void> signInWithEmail(String email) async {
    final trimmed = email.trim();
    if (trimmed.isEmpty || !trimmed.contains('@')) {
      throw ArgumentError('Ingresa un email válido');
    }
    await _client.auth.signInWithOtp(email: trimmed);
  }

  @override
  Future<void> continueAnonymously() async {
    await _client.auth.signInAnonymously();
  }

  @override
  Future<void> signOut() => _client.auth.signOut();

  @override
  String? get currentAccessToken => _client.auth.currentSession?.accessToken;

  @override
  Stream<String?> get accessTokenChanges =>
      _client.auth.onAuthStateChange.map((event) => event.session?.accessToken);
}
