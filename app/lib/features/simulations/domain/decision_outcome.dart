/// What Agente 12 (Aprendizaje) concluded after the user reported what
/// actually happened. Mirrors `DecisionOutcomeResponse`
/// (backend/src/core_api/simulations/api/schemas.py).
class DecisionOutcome {
  const DecisionOutcome({
    required this.id,
    required this.decisionId,
    required this.reportedOutcome,
    required this.closestScenarioId,
    required this.calibrationDelta,
    required this.systemErrorsIdentified,
    required this.reportedAt,
  });

  final String id;
  final String decisionId;
  final String reportedOutcome;

  /// `null` when what happened matched no generated scenario. docs/
  /// REALITY_ENGINE.md §2 calls that a "blind spot" and is explicit that it
  /// is a valuable result, never to be forced into a false match — so the
  /// client shows it as such rather than hiding it or picking a nearest
  /// scenario of its own.
  final String? closestScenarioId;

  /// -100..100 (`CalibrationOutput.calibration_delta`). The exact meaning of
  /// the sign is not specified anywhere in docs/REALITY_ENGINE.md, and
  /// `UserBiasProfile.with_calibration_delta` calls its own formula "a
  /// starting formula, not a validated calibration model" — so this is
  /// rendered as a number and a position, never dressed up as "acertamos un
  /// 72%".
  final double calibrationDelta;

  /// What the simulation itself got wrong, in Agente 12's own words. The
  /// most honest part of the whole loop and the reason the screen shows it
  /// verbatim.
  final List<String> systemErrorsIdentified;

  final DateTime reportedAt;

  bool get matchedNoScenario => closestScenarioId == null;
}
