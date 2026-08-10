/// The minimum a screen needs to open a decision's result: its id, and the
/// title to show while the simulation loads.
///
/// Passed as GoRouter `extra` rather than in the path — a decision's title
/// is user-written free text, and URL-encoding it would make the route both
/// ugly and lossy. The id alone would be enough for correctness, but then
/// the app bar would sit empty until the first request returned.
class DecisionRef {
  const DecisionRef({required this.id, required this.title});

  final String id;
  final String title;
}
