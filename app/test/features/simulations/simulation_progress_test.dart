import 'package:flutter_test/flutter_test.dart';
import 'package:var_os_app/features/simulations/domain/simulation_progress.dart';

void main() {
  test(
    'every declared group covers at least one stage id, with no overlap',
    () {
      final seen = <String>{};
      for (final group in SimulationStageGroup.values) {
        expect(group.stageIds, isNotEmpty);
        for (final id in group.stageIds) {
          expect(seen.contains(id), isFalse, reason: '$id claimed twice');
          seen.add(id);
        }
      }
    },
  );

  test('forStageId resolves a known agent to its row', () {
    expect(
      SimulationStageGroup.forStageId('scenario_generation'),
      SimulationStageGroup.scenarios,
    );
    expect(
      SimulationStageGroup.forStageId('risk_analysis'),
      SimulationStageGroup.risks,
    );
  });

  test('forStageId returns null for an agent this build has no row for', () {
    // A new agent shouldn't crash the stream — it just lights up nothing,
    // same posture the backend takes toward an id it doesn't recognize.
    expect(SimulationStageGroup.forStageId('some_future_agent'), isNull);
  });

  test('a group with no events at all reads as not started', () {
    const progress = LiveSimulationProgress();

    expect(
      progress.statusFor(SimulationStageGroup.understanding),
      StageStatus.notStarted,
    );
  });

  test('a group is in progress once any of its stages has started', () {
    const event = SimulationStageProgress(
      stage: 'safety_gate',
      status: 'started',
    );
    final progress = const LiveSimulationProgress().withEvent(event);

    expect(
      progress.statusFor(SimulationStageGroup.understanding),
      StageStatus.inProgress,
    );
  });

  test('a group is done only once every one of its stages has completed', () {
    var progress = const LiveSimulationProgress();
    for (final stage in const ['safety_gate', 'comprehension']) {
      progress = progress.withEvent(
        SimulationStageProgress(stage: stage, status: 'completed'),
      );
    }

    // "summary" (the third agent in this row) never fired — the row must
    // still read as in progress, not done, even though the two agents it
    // did hear about both finished.
    expect(
      progress.statusFor(SimulationStageGroup.understanding),
      StageStatus.inProgress,
    );

    progress = progress.withEvent(
      const SimulationStageProgress(stage: 'summary', status: 'completed'),
    );

    expect(
      progress.statusFor(SimulationStageGroup.understanding),
      StageStatus.done,
    );
  });

  test('a later event for the same stage overwrites its earlier status', () {
    var progress = const LiveSimulationProgress().withEvent(
      const SimulationStageProgress(stage: 'ranking', status: 'started'),
    );
    expect(
      progress.statusFor(SimulationStageGroup.comparing),
      StageStatus.inProgress,
    );

    progress = progress.withEvent(
      const SimulationStageProgress(stage: 'ranking', status: 'completed'),
    );
    // `comparison` (the row's other agent) never fired, so the row is still
    // in progress overall — this only checks the single stage's own status
    // flipped from started to completed.
    expect(progress.stageStatuses['ranking'], StageStatus.done);
  });
}
