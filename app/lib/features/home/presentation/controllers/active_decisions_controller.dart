import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_client.dart';
import '../../data/api_decisions_repository.dart';
import '../../domain/decision_summary.dart';
import '../../domain/decisions_repository.dart';

final decisionsRepositoryProvider = Provider<DecisionsRepository>(
  (ref) => ApiDecisionsRepository(ref.read(dioProvider)),
);

/// Loads the caller's active decisions (`draft`/`clarifying`/`simulating`
/// — docs/UX_DESIGN.md Pantalla 4's "Decisiones activas") on first watch,
/// and again whenever `refresh()` is called (e.g. pull-to-refresh).
class ActiveDecisionsController extends AsyncNotifier<List<DecisionSummary>> {
  @override
  Future<List<DecisionSummary>> build() => _fetchActive();

  Future<void> refresh() async {
    state = const AsyncLoading<List<DecisionSummary>>().copyWithPrevious(state);
    state = await AsyncValue.guard(_fetchActive);
  }

  Future<List<DecisionSummary>> _fetchActive() async {
    final all = await ref.read(decisionsRepositoryProvider).listDecisions();
    return all.where((decision) => decision.isActive).toList();
  }
}

final activeDecisionsControllerProvider =
    AsyncNotifierProvider<ActiveDecisionsController, List<DecisionSummary>>(
      ActiveDecisionsController.new,
    );
