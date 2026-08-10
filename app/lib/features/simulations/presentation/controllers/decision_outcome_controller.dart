import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../memory/presentation/controllers/bias_profile_controller.dart';
import '../../domain/decision_outcome.dart';
import '../../domain/simulations_repository.dart';
import 'decision_simulation_controller.dart';
import 'outcomes_controller.dart';

class DecisionOutcomeState {
  const DecisionOutcomeState({
    this.outcome,
    this.isSubmitting = false,
    this.errorMessage,
  });

  /// What Agente 12 concluded, once this decision's loop has been closed —
  /// whether that happened just now or in an earlier session.
  final DecisionOutcome? outcome;
  final bool isSubmitting;
  final String? errorMessage;

  bool get isReported => outcome != null;
}

/// Owns closing the loop for one decision (docs/PRD.md CU8, docs/UX_DESIGN.md
/// Pantalla 11).
///
/// The initial state is derived from the shared `GET /v1/outcomes` read, so
/// a decision whose loop was closed in an earlier session opens showing that
/// result rather than re-offering the prompt.
class DecisionOutcomeController
    extends FamilyAsyncNotifier<DecisionOutcomeState, String> {
  @override
  Future<DecisionOutcomeState> build(String decisionId) async {
    final outcomes = await ref.watch(outcomesControllerProvider.future);
    return DecisionOutcomeState(outcome: _find(outcomes, decisionId));
  }

  DecisionOutcome? _find(List<DecisionOutcome> outcomes, String decisionId) {
    for (final outcome in outcomes) {
      if (outcome.decisionId == decisionId) return outcome;
    }
    return null;
  }

  Future<void> report(String reportedOutcome) async {
    final text = reportedOutcome.trim();
    final current = state.valueOrNull ?? const DecisionOutcomeState();
    if (text.isEmpty || current.isSubmitting || current.isReported) return;

    state = const AsyncData(DecisionOutcomeState(isSubmitting: true));

    try {
      final outcome = await ref
          .read(simulationsRepositoryProvider)
          .reportOutcome(decisionId: arg, reportedOutcome: text);
      // Closing the loop is the one action in the app that rewrites the
      // user's bias profile, which is the whole content of Pantalla 12 —
      // so Memoria must not keep showing the pre-calibration state. The
      // outcomes list feeds Mis Decisiones' "sin cerrar el ciclo"
      // indicator, so it goes stale on the same write.
      await ref.read(biasProfileControllerProvider.notifier).refresh();
      await ref.read(outcomesControllerProvider.notifier).refresh();
      state = AsyncData(DecisionOutcomeState(outcome: outcome));
    } on OutcomeConflictError {
      await _resolveConflict();
    } on CalibrationUnavailableError {
      state = const AsyncData(
        DecisionOutcomeState(
          errorMessage:
              'La calibración no está disponible ahora mismo. No se guardó '
              'nada — podés volver a intentarlo.',
        ),
      );
    } catch (error) {
      state = const AsyncData(
        DecisionOutcomeState(errorMessage: 'No pudimos registrar lo que pasó.'),
      );
    }
  }

  /// The backend answers 409 both for "this loop is already closed" and for
  /// "this decision has no completed simulation", with only prose to tell
  /// them apart. Rather than match that string across a service boundary,
  /// ask the source of truth: if an outcome for this decision exists, the
  /// loop was closed (elsewhere, or by a double tap) and showing it is the
  /// truthful answer; if not, the conflict was the other one.
  Future<void> _resolveConflict() async {
    final List<DecisionOutcome> outcomes;
    try {
      outcomes = await ref.read(simulationsRepositoryProvider).listOutcomes();
    } catch (error) {
      state = const AsyncData(
        DecisionOutcomeState(errorMessage: 'No pudimos registrar lo que pasó.'),
      );
      return;
    }

    final existing = _find(outcomes, arg);
    if (existing != null) {
      // Refreshed only in this branch: the other one must not rebuild this
      // controller, or the message below would be discarded.
      await ref.read(outcomesControllerProvider.notifier).refresh();
      state = AsyncData(DecisionOutcomeState(outcome: existing));
      return;
    }

    state = const AsyncData(
      DecisionOutcomeState(
        errorMessage:
            'Primero necesitás simular esta decisión para poder comparar '
            'lo que pasó con lo que el sistema anticipó.',
      ),
    );
  }
}

final decisionOutcomeControllerProvider =
    AsyncNotifierProvider.family<
      DecisionOutcomeController,
      DecisionOutcomeState,
      String
    >(DecisionOutcomeController.new);
