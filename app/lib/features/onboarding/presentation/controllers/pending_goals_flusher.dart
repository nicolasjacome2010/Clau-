import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../auth/presentation/controllers/session_controller.dart';
import '../../../goals/domain/goals_repository.dart';
import '../../../goals/presentation/controllers/goals_controller.dart';
import '../../data/preferences_pending_goals_store.dart';
import '../../domain/pending_goals_store.dart';

final pendingGoalsStoreProvider = Provider<PendingGoalsStore>(
  (ref) => PreferencesPendingGoalsStore(),
);

/// Delivers the goals captured in Onboarding to the backend at the first
/// moment there is a session to authenticate the call with.
///
/// `build` watches the session token, so this runs itself the instant one
/// appears — whether that's seconds after Onboarding or a fresh process
/// launched by a magic link. It needs no trigger from any screen, which is
/// what makes it correct for the magic-link path, where `AuthScreen`'s own
/// success listener may never fire in the process that captured the goals.
///
/// **Goals are submitted one at a time, and the remainder is rewritten
/// after each success.** A failure stops the run and leaves exactly the
/// un-submitted goals queued, so a retry can never duplicate the ones that
/// already landed — the alternative (clear-all-at-the-end) turns any
/// mid-flight network blip into either lost goals or duplicated ones.
class PendingGoalsFlusher extends AsyncNotifier<int> {
  /// How many goals this run delivered. Nothing renders it today; it's the
  /// honest return value of the operation, and what the tests assert on.
  @override
  Future<int> build() async {
    final token = ref.watch(sessionControllerProvider);
    if (token == null) return 0;
    return _flush();
  }

  Future<int> _flush() async {
    final store = ref.read(pendingGoalsStoreProvider);
    var pending = await store.read();
    if (pending.isEmpty) return 0;

    final goals = ref.read(goalsRepositoryProvider);
    var submitted = 0;
    for (final name in [...pending]) {
      try {
        await goals.createGoal(name: name);
      } on GoalsRepositoryError {
        // Stop rather than continue: if the backend is unreachable the
        // next goal will fail too, and whatever is left stays queued for
        // the next session either way.
        break;
      }
      pending = [...pending]..remove(name);
      await store.write(pending);
      submitted += 1;
    }

    if (submitted > 0) {
      // Perfil de Objetivos may already have read an empty list.
      ref.invalidate(goalsControllerProvider);
    }
    return submitted;
  }
}

final pendingGoalsFlusherProvider =
    AsyncNotifierProvider<PendingGoalsFlusher, int>(PendingGoalsFlusher.new);
