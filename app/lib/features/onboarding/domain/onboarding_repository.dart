/// Port for persisting the goals captured during onboarding.
///
/// Deliberately not called during onboarding itself: goal capture
/// (docs/UX_DESIGN.md, Pantalla 2 Paso 3) happens before authentication in
/// the real product flow (Pantalla 3 allows "probar antes de registrarse"),
/// and the backend's `POST /v1/goals` requires a Supabase JWT
/// (backend/src/core_api/goals/api/router.py). Until this app has a real
/// Supabase Auth adapter, `OnboardingController`'s selections only live in
/// memory; wiring an `ApiGoalsRepository` to submit them right after the
/// first authenticated request (mirroring `GetOrCreateUserUseCase`'s JIT
/// provisioning) is the next integration increment, not a forgotten piece —
/// same "documented, not silent" gap as `core/network/api_client.dart`'s
/// missing token-refresh interceptor.
abstract class OnboardingRepository {
  Future<void> submitInitialGoals({
    required Set<String> seedGoalIds,
    required List<String> customGoals,
  });
}
