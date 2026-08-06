import 'dart:async';

import 'package:var_os_app/features/simulations/domain/decision_outcome.dart';
import 'package:var_os_app/features/simulations/domain/simulation.dart';
import 'package:var_os_app/features/simulations/domain/simulation_progress.dart';
import 'package:var_os_app/features/simulations/domain/simulations_repository.dart';

class FakeSimulationsRepository implements SimulationsRepository {
  FakeSimulationsRepository({
    List<Simulation>? simulations,
    this.listError,
    this.runError,
    this.ranSimulation,
    this.runGate,
    this.streamStages,
    this.outcomeError,
    this.reportedOutcome,
    this.outcomeGate,
    this.outcomesError,
    List<DecisionOutcome>? closedLoops,
  }) : simulations = simulations ?? const [],
       _closedLoops = closedLoops ?? const [];

  final List<Simulation> simulations;
  final SimulationsRepositoryError? listError;
  final SimulationsRepositoryError? runError;
  final SimulationsRepositoryError? outcomeError;

  /// Stage events `runSimulationStream` yields before its terminal event —
  /// `null` skips straight to the result/error, same as a run that never
  /// reported progress.
  final List<SimulationStageProgress>? streamStages;

  /// What `reportOutcome` returns on success.
  final DecisionOutcome? reportedOutcome;

  /// Same purpose as `runGate`, for the calibration round trip.
  final Completer<void>? outcomeGate;

  final SimulationsRepositoryError? outcomesError;

  /// What `GET /v1/outcomes` would answer — loops closed before this
  /// session, plus anything reported during it.
  List<DecisionOutcome> _closedLoops;

  /// What `runSimulation` returns on success. Left `null` when a test only
  /// cares about the failure path.
  final Simulation? ranSimulation;

  /// Held open until the test completes it, so the in-flight state is
  /// observable. Without it the fake resolves on the first microtask and the
  /// running indicator never gets a frame — which would make "we show an
  /// honest wait while `/v1/simulate` blocks for 15-30s" untestable.
  final Completer<void>? runGate;

  /// Every decision id `runSimulation` was called with, in order.
  final List<String> runCalls = [];

  /// How many times `listOutcomes` was called — lets a test assert that a
  /// list screen costs one read, not one per row.
  int outcomesReads = 0;

  /// Every `reportOutcome` call, in order — lets a test assert on exactly
  /// what would reach `POST /v1/decisions/{id}/outcome`.
  final List<({String decisionId, String reportedOutcome})> outcomeCalls = [];

  @override
  Future<List<Simulation>> listForDecision(String decisionId) async {
    if (listError != null) throw listError!;
    return simulations.where((s) => s.decisionId == decisionId).toList();
  }

  @override
  Future<Simulation> runSimulation(String decisionId) async {
    runCalls.add(decisionId);
    if (runGate != null) await runGate!.future;
    if (runError != null) throw runError!;
    return ranSimulation ??
        testSimulation(
          id: 'ran',
          decisionId: decisionId,
          scenarios: [
            testScenario(id: 's1', title: 'Escenario nuevo', rank: 1),
          ],
        );
  }

  @override
  Stream<SimulationProgressEvent> runSimulationStream(
    String decisionId,
  ) async* {
    runCalls.add(decisionId);
    for (final stage in streamStages ?? const <SimulationStageProgress>[]) {
      yield stage;
    }
    if (runGate != null) await runGate!.future;
    if (runError != null) throw runError!;
    yield SimulationProgressResult(
      ranSimulation ??
          testSimulation(
            id: 'ran',
            decisionId: decisionId,
            scenarios: [
              testScenario(id: 's1', title: 'Escenario nuevo', rank: 1),
            ],
          ),
    );
  }

  /// Simulates the loop being closed by someone else (another device, a
  /// double tap that raced) between one read and the next.
  void closeLoopBehindOurBack(DecisionOutcome outcome) {
    _closedLoops = [..._closedLoops, outcome];
  }

  @override
  Future<List<DecisionOutcome>> listOutcomes() async {
    outcomesReads += 1;
    if (outcomesError != null) throw outcomesError!;
    return _closedLoops;
  }

  @override
  Future<DecisionOutcome> reportOutcome({
    required String decisionId,
    required String reportedOutcome,
  }) async {
    outcomeCalls.add((
      decisionId: decisionId,
      reportedOutcome: reportedOutcome,
    ));
    if (outcomeGate != null) await outcomeGate!.future;
    if (outcomeError != null) throw outcomeError!;
    final outcome =
        this.reportedOutcome ??
        testOutcome(decisionId: decisionId, reportedOutcome: reportedOutcome);
    // The real backend would return it from `GET /v1/outcomes` afterwards.
    _closedLoops = [..._closedLoops, outcome];
    return outcome;
  }
}

DecisionOutcome testOutcome({
  String id = 'outcome-1',
  String decisionId = 'd1',
  String reportedOutcome = 'Acepté la oferta.',
  String? closestScenarioId,
  double calibrationDelta = 0,
  List<String> systemErrorsIdentified = const [],
  DateTime? reportedAt,
}) {
  return DecisionOutcome(
    id: id,
    decisionId: decisionId,
    reportedOutcome: reportedOutcome,
    closestScenarioId: closestScenarioId,
    calibrationDelta: calibrationDelta,
    systemErrorsIdentified: systemErrorsIdentified,
    reportedAt: reportedAt ?? DateTime.utc(2026, 7, 1),
  );
}

/// Builds a `Simulation` with defaults for everything a given test isn't
/// about — same idea as `testDecision` in `../decisions/fakes.dart`.
Simulation testSimulation({
  String id = 'sim-1',
  String decisionId = 'd1',
  String status = 'completed',
  bool safeToProceed = true,
  String recommendedAction = 'proceed',
  List<SimulationScenario>? scenarios,
  String? synthesisText,
  String? reflectiveQuestion,
  DateTime? startedAt,
  DateTime? completedAt,
}) {
  return Simulation(
    id: id,
    decisionId: decisionId,
    status: status,
    safetyGate: SafetyGateResult(
      safeToProceed: safeToProceed,
      recommendedAction: recommendedAction,
    ),
    scenarios: scenarios ?? const [],
    synthesisText: synthesisText,
    reflectiveQuestion: reflectiveQuestion,
    startedAt: startedAt ?? DateTime.utc(2026, 1, 1),
    completedAt: completedAt,
  );
}

SimulationScenario testScenario({
  required String id,
  required String title,
  required int rank,
  String narrative = 'Lo que podría pasar en este escenario.',
  List<String> assumptions = const [],
  double relativeProbability = 40,
  int timeHorizonMonths = 12,
  List<GoalAlignment> goalAlignmentScores = const [],
  double riskScore = 30,
  double reversibilityScore = 70,
  double finalScore = 60,
}) {
  return SimulationScenario(
    id: id,
    title: title,
    narrative: narrative,
    assumptions: assumptions,
    relativeProbability: relativeProbability,
    timeHorizonMonths: timeHorizonMonths,
    goalAlignmentScores: goalAlignmentScores,
    riskScore: riskScore,
    reversibilityScore: reversibilityScore,
    finalScore: finalScore,
    rank: rank,
  );
}
