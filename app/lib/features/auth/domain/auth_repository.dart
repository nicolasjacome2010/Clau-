/// Port for Supabase Auth (docs/ARCHITECTURE.md §8: "servicios internos
/// nunca hablan directo con Supabase Auth" — the same posture applies to
/// this client, which depends on this interface, never on a concrete
/// Supabase SDK call, from presentation code).
///
/// `SupabaseAuthRepository` (`data/supabase_auth_repository.dart`) is the
/// production implementation. `LocalStubAuthRepository` remains as the
/// binding used when a build carries no Supabase project — see
/// `data/supabase_config.dart` for how that choice is made and why it is
/// visible rather than silent.
abstract class AuthRepository {
  /// Sends a magic link / OTP. Deliberately does *not* return a session:
  /// the user finishes signing in from their mail client, so the session
  /// arrives asynchronously through [accessTokenChanges].
  Future<void> signInWithEmail(String email);

  /// docs/UX_DESIGN.md Pantalla 3's "probar sin cuenta" — a real Supabase
  /// anonymous user, not a local pretend session, so the Core API can do
  /// its JIT provisioning against a genuine JWT exactly as it would for
  /// anyone else (`GetOrCreateUserUseCase`).
  Future<void> continueAnonymously();

  /// Ends the session. Called after an erasure: keeping a token for a
  /// user whose rows are gone would leave every screen 404-ing with no
  /// explanation.
  Future<void> signOut();

  /// The current access token, or `null` when there is no session.
  ///
  /// Synchronous because the Dio interceptor needs it on every request; the
  /// SDK keeps it fresh in the background, so reading it is a memory
  /// lookup, never a network call.
  String? get currentAccessToken;

  /// Emits on every sign-in, sign-out and silent token refresh. This is
  /// what closes the "no automatic refresh" gap `core/network/api_client.dart`
  /// used to document: the app never refreshes a token itself, it just
  /// follows the session.
  Stream<String?> get accessTokenChanges;
}
