import 'package:var_os_app/features/decisions/domain/decision_summary.dart';
import 'package:var_os_app/features/decisions/domain/decisions_repository.dart';

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

/// Builds a `DecisionSummary` with sensible defaults for the fields most
/// tests don't care about, so call sites only need to spell out what the
/// test is actually about (title/status, usually).
DecisionSummary testDecision({
  required String id,
  required String title,
  String vertical = 'career',
  required String status,
  DateTime? createdAt,
  DateTime? updatedAt,
}) {
  final created = createdAt ?? DateTime.utc(2026, 1, 1);
  return DecisionSummary(
    id: id,
    title: title,
    vertical: vertical,
    status: status,
    createdAt: created,
    updatedAt: updatedAt ?? created,
  );
}
