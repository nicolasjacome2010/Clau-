import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../goals/domain/goal_option.dart';
import 'pending_goals_flusher.dart';

/// Local onboarding state: which of the 3 steps (docs/UX_DESIGN.md,
/// Pantalla 2) is showing, and which goals the user picked in Paso 3 (seed
/// chip ids + free-text custom entries). Submitting them can't happen here
/// — the user isn't authenticated yet — so `finish()` hands them to
/// `PendingGoalsStore` and `PendingGoalsFlusher` delivers them once there
/// is a session (see `pending_goals_store.dart` for why that indirection
/// is the ordering, not a workaround).
class OnboardingState {
  const OnboardingState({
    this.step = 0,
    this.selectedGoalIds = const {},
    this.customGoals = const [],
  });

  static const int totalSteps = 3;

  final int step;
  final Set<String> selectedGoalIds;
  final List<String> customGoals;

  bool get isLastStep => step == totalSteps - 1;
  bool get hasAnyGoalSelected =>
      selectedGoalIds.isNotEmpty || customGoals.isNotEmpty;

  /// What actually reaches `POST /v1/goals`: the seed chips resolved to
  /// their labels, then the user's own entries.
  ///
  /// Iterating `seedOptions` rather than `selectedGoalIds` is deliberate —
  /// it gives the backend the spec's own chip order instead of whatever
  /// order the user happened to tap, and drops an id that no longer
  /// matches a chip rather than inventing a name for it.
  List<String> get selectedGoalNames => [
    for (final option in GoalOption.seedOptions)
      if (selectedGoalIds.contains(option.id)) option.label,
    ...customGoals,
  ];

  OnboardingState copyWith({
    int? step,
    Set<String>? selectedGoalIds,
    List<String>? customGoals,
  }) {
    return OnboardingState(
      step: step ?? this.step,
      selectedGoalIds: selectedGoalIds ?? this.selectedGoalIds,
      customGoals: customGoals ?? this.customGoals,
    );
  }
}

class OnboardingController extends Notifier<OnboardingState> {
  @override
  OnboardingState build() => const OnboardingState();

  void goToStep(int step) {
    if (step >= 0 && step < OnboardingState.totalSteps) {
      state = state.copyWith(step: step);
    }
  }

  void nextStep() {
    if (!state.isLastStep) {
      state = state.copyWith(step: state.step + 1);
    }
  }

  void toggleGoal(String goalId) {
    final updated = {...state.selectedGoalIds};
    if (!updated.remove(goalId)) {
      updated.add(goalId);
    }
    state = state.copyWith(selectedGoalIds: updated);
  }

  void addCustomGoal(String label) {
    final trimmed = label.trim();
    if (trimmed.isEmpty || state.customGoals.contains(trimmed)) return;
    state = state.copyWith(customGoals: [...state.customGoals, trimmed]);
  }

  /// Hands the selection to the device queue, on the way out of Onboarding.
  ///
  /// Awaited by the screen before it navigates: the whole point is that
  /// this survives the app process ending, so it has to be on disk before
  /// the user can reach a flow (magic link) that ends it.
  Future<void> finish() async {
    await ref.read(pendingGoalsStoreProvider).write(state.selectedGoalNames);
  }
}

final onboardingControllerProvider =
    NotifierProvider<OnboardingController, OnboardingState>(
      OnboardingController.new,
    );
