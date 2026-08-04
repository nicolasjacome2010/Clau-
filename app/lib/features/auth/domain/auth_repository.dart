/// Port for Supabase Auth (docs/ARCHITECTURE.md §8: "servicios internos
/// nunca hablan directo con Supabase Auth" — the same posture applies to
/// this client, which should depend on this interface, never a concrete
/// Supabase SDK call, from presentation code).
///
/// No concrete production implementation ships in this increment: there
/// are no Supabase project credentials available yet. `LocalStubAuthRepository`
/// (`data/local_stub_auth_repository.dart`) is the interim default binding
/// so `auth_screen.dart` is fully built and tested against this interface
/// now — wiring a real `SupabaseAuthRepository` later requires no screen
/// changes, the same Dependency Inversion the backend applies to
/// `RealityEngineClient`/`StripeClient`.
abstract class AuthRepository {
  Future<void> signInWithEmail(String email);
  Future<void> continueAnonymously();
}
