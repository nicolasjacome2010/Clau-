/// A row from the backend's `GET /v1/decisions` (list, not detail) —
/// mirrors `DecisionResponse` in `backend/src/core_api/decisions/api/
/// schemas.py` field for field, but as this app's own plain value type,
/// never a shared model. `vertical`/`status` stay as raw wire strings
/// here (not a Dart enum): the set of valid values is owned by the
/// backend's `DecisionVertical`/`DecisionStatus`, and duplicating that
/// enum client-side would just be one more place to keep in sync.
class DecisionSummary {
  const DecisionSummary({
    required this.id,
    required this.title,
    required this.vertical,
    required this.status,
  });

  final String id;
  final String title;
  final String vertical;
  final String status;

  static const activeStatuses = {'draft', 'clarifying', 'simulating'};

  bool get isActive => activeStatuses.contains(status);
}
