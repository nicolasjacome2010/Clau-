import '../domain/auth_repository.dart';

/// Interim stand-in for a real Supabase Auth adapter (see the port's
/// docstring for why). Accepts any non-empty email and never actually
/// talks to a network — this must be swapped for `SupabaseAuthRepository`
/// before any real user data flows through this app; the loud class name
/// is deliberate so it can't be mistaken for a production implementation.
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
}
