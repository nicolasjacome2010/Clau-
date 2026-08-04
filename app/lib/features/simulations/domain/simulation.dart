/// How one scenario scores against one of the user's goals — an entry of
/// `goal_alignment_scores` (backend/src/core_api/simulations/api/schemas.py),
/// which the backend types as a loose `dict[str, Any]` because Reality
/// Engine owns its shape (docs/REALITY_ENGINE.md, Agente 8).
class GoalAlignment {
  const GoalAlignment({
    required this.goal,
    required this.score,
    required this.justification,
  });

  final String goal;
  final double score;
  final String justification;
}

/// One simulated scenario. Mirrors `SimulationScenarioResponse`.
class SimulationScenario {
  const SimulationScenario({
    required this.id,
    required this.title,
    required this.narrative,
    required this.assumptions,
    required this.relativeProbability,
    required this.timeHorizonMonths,
    required this.goalAlignmentScores,
    required this.riskScore,
    required this.reversibilityScore,
    required this.finalScore,
    required this.rank,
  });

  final String id;
  final String title;
  final String narrative;
  final List<String> assumptions;
  final double relativeProbability;
  final int timeHorizonMonths;
  final List<GoalAlignment> goalAlignmentScores;
  final double riskScore;
  final double reversibilityScore;
  final double finalScore;
  final int rank;

  bool get isTopRanked => rank == 1;
}

/// What the Safety Gate (Agente 0) decided for this run. Kept as its own
/// type rather than a raw map so the one place that matters — "did this
/// halt?" — is a named question, not a string comparison at the call site.
class SafetyGateResult {
  const SafetyGateResult({
    required this.safeToProceed,
    required this.recommendedAction,
  });

  final bool safeToProceed;
  final String recommendedAction;

  /// docs/PRD.md §18: on a halt the product must refuse to simulate and
  /// redirect to professional help — never render scenarios anyway.
  bool get requiresReferral =>
      !safeToProceed || recommendedAction == 'halt_and_refer';
}

/// Mirrors `SimulationResponse`.
class Simulation {
  const Simulation({
    required this.id,
    required this.decisionId,
    required this.status,
    required this.safetyGate,
    required this.scenarios,
    required this.synthesisText,
    required this.reflectiveQuestion,
    required this.startedAt,
    required this.completedAt,
  });

  final String id;
  final String decisionId;

  /// `completed` | `partial` | `failed` — the reachable subset of
  /// docs/DATABASE.md §2.5's enum (see `SimulationStatus` on the backend).
  final String status;
  final SafetyGateResult safetyGate;
  final List<SimulationScenario> scenarios;
  final String? synthesisText;
  final String? reflectiveQuestion;
  final DateTime startedAt;
  final DateTime? completedAt;

  bool get isCompleted => status == 'completed';
  bool get isFailed => status == 'failed';

  /// Scenarios ordered as the spec wants them shown (docs/UX_DESIGN.md
  /// Pantalla 7: "orden por defecto: por `rank`").
  List<SimulationScenario> get rankedScenarios {
    final ordered = [...scenarios]..sort((a, b) => a.rank.compareTo(b.rank));
    return ordered;
  }
}
