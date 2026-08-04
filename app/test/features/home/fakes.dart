import 'package:var_os_app/features/home/domain/decision_summary.dart';
import 'package:var_os_app/features/home/domain/decisions_repository.dart';

class FakeDecisionsRepository implements DecisionsRepository {
  FakeDecisionsRepository({List<DecisionSummary>? decisions, this.error})
    : decisions = decisions ?? const [];

  final List<DecisionSummary> decisions;
  final DecisionsRepositoryError? error;

  @override
  Future<List<DecisionSummary>> listDecisions() async {
    if (error != null) throw error!;
    return decisions;
  }
}
