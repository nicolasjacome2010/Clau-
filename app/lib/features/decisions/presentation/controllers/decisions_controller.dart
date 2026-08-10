import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_client.dart';
import '../../data/api_decisions_repository.dart';
import '../../domain/decision_summary.dart';
import '../../domain/decisions_repository.dart';

final decisionsRepositoryProvider = Provider<DecisionsRepository>(
  (ref) => ApiDecisionsRepository(ref.read(dioProvider)),
);

/// Loads *all* of the caller's decisions on first watch, and again
/// whenever `refresh()` is called. Deliberately unfiltered: both Home's
/// "Decisiones activas" (Pantalla 4) and "Mis Decisiones" (Pantalla 10,
/// grouped by Activas/Completadas/Archivadas) derive their own view from
/// this single shared list — Riverpod dedupes the provider, so switching
/// between those two tabs in the same nav shell never triggers a second
/// `GET /v1/decisions` call.
class DecisionsController extends AsyncNotifier<List<DecisionSummary>> {
  @override
  Future<List<DecisionSummary>> build() => _fetch();

  Future<void> refresh() async {
    state = const AsyncLoading<List<DecisionSummary>>().copyWithPrevious(state);
    state = await AsyncValue.guard(_fetch);
  }

  Future<List<DecisionSummary>> _fetch() {
    return ref.read(decisionsRepositoryProvider).listDecisions();
  }
}

final decisionsControllerProvider =
    AsyncNotifierProvider<DecisionsController, List<DecisionSummary>>(
      DecisionsController.new,
    );
