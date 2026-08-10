/// One of the user's weighted decision goals — mirrors `GoalResponse`
/// (backend/src/core_api/goals/api/schemas.py) field for field, as this
/// app's own plain value type.
class Goal {
  const Goal({
    required this.id,
    required this.name,
    required this.defaultWeight,
    required this.isActive,
  });

  final String id;
  final String name;

  /// 0..100 (the backend validates the range).
  final int defaultWeight;
  final bool isActive;
}
