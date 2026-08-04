import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../memory/presentation/controllers/bias_profile_controller.dart';
import '../../domain/decision_outcome.dart';
import '../../domain/simulations_repository.dart';
import 'decision_simulation_controller.dart';

class DecisionOutcomeState {
  const DecisionOutcomeState({
    this.outcome,
    this.isSubmitting = false,
    this.errorMessage,
  });

  /// What Agente 12 returned, once the loop has been closed **in this
  /// session**. It is never populated on open, because the backend exposes
  /// no `GET .../outcome` to ask with.
  final DecisionOutcome? outcome;
  final bool isSubmitting;
  final String? errorMessage;

  bool get isReported => outcome != null;
}

/// Owns closing the loop for one decision (docs/PRD.md CU8, docs/UX_DESIGN.md
/// Pantalla 11).
///
/// A plain `Notifier`, not an `AsyncNotifier`: there is nothing to load.
/// `POST /v1/decisions/{id}/outcome` has no `GET` counterpart, so on opening
/// a decision the client genuinely cannot know whether its loop was already
/// closed — and it says so by simply offering the prompt, rather than
/// guessing from `updated_at` or caching a claim it can't verify. The cost
/// is real and documented in `app/README.md`: a user who reports twice
/// calibrates twice, since `ReportDecisionOutcomeUseCase` has no duplicate
/// guard either. Fixing that belongs in the backend (a `GET`, or an upsert
/// keyed on `decision_id`), not in a client-side workaround.
class DecisionOutcomeController
    extends FamilyNotifier<DecisionOutcomeState, String> {
  @override
  DecisionOutcomeState build(String decisionId) => const DecisionOutcomeState();

  Future<void> report(String reportedOutcome) async {
    final text = reportedOutcome.trim();
    if (text.isEmpty || state.isSubmitting) return;

    state = const DecisionOutcomeState(isSubmitting: true);

    try {
      final outcome = await ref
          .read(simulationsRepositoryProvider)
          .reportOutcome(decisionId: arg, reportedOutcome: text);
      // Closing the loop is the one action in the app that rewrites the
      // user's bias profile, which is the whole content of Pantalla 12 —
      // so Memoria must not keep showing the pre-calibration state.
      await ref.read(biasProfileControllerProvider.notifier).refresh();
      state = DecisionOutcomeState(outcome: outcome);
    } on NoCompletedSimulationError {
      state = const DecisionOutcomeState(
        errorMessage:
            'Primero necesitás simular esta decisión para poder comparar '
            'lo que pasó con lo que el sistema anticipó.',
      );
    } on CalibrationUnavailableError {
      state = const DecisionOutcomeState(
        errorMessage:
            'La calibración no está disponible ahora mismo. No se guardó '
            'nada — podés volver a intentarlo.',
      );
    } catch (error) {
      state = const DecisionOutcomeState(
        errorMessage: 'No pudimos registrar lo que pasó.',
      );
    }
  }
}

final decisionOutcomeControllerProvider =
    NotifierProvider.family<
      DecisionOutcomeController,
      DecisionOutcomeState,
      String
    >(DecisionOutcomeController.new);
