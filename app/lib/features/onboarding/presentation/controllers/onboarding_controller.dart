import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Local onboarding state: which of the 3 steps (docs/UX_DESIGN.md,
/// Pantalla 2) is showing, and which goals the user picked in Paso 3 (seed
/// chip ids + free-text custom entries). See `onboarding_repository.dart`
/// for why submitting this to the backend is deferred rather than done here.
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
}

final onboardingControllerProvider =
    NotifierProvider<OnboardingController, OnboardingState>(
      OnboardingController.new,
    );
