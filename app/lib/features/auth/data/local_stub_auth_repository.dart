import '../domain/auth_repository.dart';

/// The binding used when a build carries no Supabase credentials (see
/// `supabase_config.dart`). It accepts any well-formed email, talks to no
/// network, and — deliberately — issues **no access token**: it lets the
/// screens run in a credential-less dev build without ever pretending the
/// resulting requests are authenticated. The loud class name stays so this
/// can't be mistaken for the production adapter, which is
/// `SupabaseAuthRepository`.
class LocalStubAuthRepository implements AuthRepository {
  @override
  Future<void> signInWithEmail(String email) async {
    if (email.trim().isEmpty || !email.contains('@')) {
      throw ArgumentError('Ingresa un email válido');
    }
    await Future<void>.delayed(const Duration(milliseconds: 300));
  }

  @override
  Future<void> continueAnonymously() async {
    await Future<void>.delayed(const Duration(milliseconds: 150));
  }

  @override
  Future<void> signOut() async {}

  /// Never a fabricated token: an unauthenticated request that gets a
  /// truthful 401 is better than one carrying a token no server accepts.
  @override
  String? get currentAccessToken => null;

  @override
  Stream<String?> get accessTokenChanges => const Stream<String?>.empty();
}
