import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/decision_outcome.dart';
import 'decision_simulation_controller.dart';

/// Every loop the user has already closed, fetched once and shared.
///
/// Same shape and reasoning as `DecisionsController`: two screens need this
/// (Mis Decisiones, to know which completed decisions are still open, and
/// the result screen, to know whether *this* one is) and Riverpod's dedup
/// means neither pays for the other's read. Reading `GET /v1/outcomes` once
/// is also the whole point of that endpoint being a collection — asking per
/// decision would be an N+1 against Pantalla 10.
class OutcomesController extends AsyncNotifier<List<DecisionOutcome>> {
  @override
  Future<List<DecisionOutcome>> build() => _fetch();

  Future<void> refresh() async {
    state = const AsyncLoading<List<DecisionOutcome>>().copyWithPrevious(state);
    state = await AsyncValue.guard(_fetch);
  }

  Future<List<DecisionOutcome>> _fetch() {
    return ref.read(simulationsRepositoryProvider).listOutcomes();
  }
}

final outcomesControllerProvider =
    AsyncNotifierProvider<OutcomesController, List<DecisionOutcome>>(
      OutcomesController.new,
    );

/// The outcome for one decision, or `null` when its loop is still open.
///
/// A derived provider rather than a per-decision request: it reads the one
/// shared list, so a screen showing fifty decisions still makes one call.
final decisionOutcomeProvider = Provider.family<DecisionOutcome?, String>((
  ref,
  decisionId,
) {
  final outcomes = ref.watch(outcomesControllerProvider).valueOrNull;
  if (outcomes == null) return null;
  for (final outcome in outcomes) {
    if (outcome.decisionId == decisionId) return outcome;
  }
  return null;
});
