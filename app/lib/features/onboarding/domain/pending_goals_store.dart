/// Device-local queue of goals captured in Onboarding that have not
/// reached the backend yet.
///
/// This exists because of a real ordering problem, not as a cache: goal
/// capture (docs/UX_DESIGN.md Pantalla 2, Paso 3) happens *before*
/// authentication — Pantalla 3 is explicit that there is no login wall
/// before showing value — while `POST /v1/goals` requires a Supabase JWT.
/// Holding the selection in memory would lose it, because the magic-link
/// flow physically leaves the app (mail client, browser) and can come back
/// to a fresh process. So the selection is written to the device the
/// moment it's final, and flushed at the first authenticated moment
/// (`PendingGoalsFlusher`) — the client-side mirror of the backend's own
/// JIT provisioning in `GetOrCreateUserUseCase`.
///
/// Goal **names**, not the seed chip ids, are what's stored: `name` is what
/// `POST /v1/goals` actually takes, so the queue holds exactly "what still
/// needs to be created" and can't be desynced by a later edit to
/// `GoalOption.seedOptions`.
abstract class PendingGoalsStore {
  Future<List<String>> read();

  /// Replaces the whole queue. There is deliberately no `remove(name)`:
  /// the flusher rewrites the remainder after each success, so the stored
  /// list is always the complete set of what is still owed to the backend
  /// — one representation of that fact, never two that can disagree.
  Future<void> write(List<String> goalNames);
}
