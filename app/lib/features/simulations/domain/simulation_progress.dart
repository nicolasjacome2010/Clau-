import 'simulation.dart';

/// One line of `POST /v1/decisions/{id}/simulations/stream`'s NDJSON body
/// (docs/UX_DESIGN.md Pantalla 6). Mirrors backend's
/// `SimulationStream*Response` schemas
/// (backend/src/core_api/simulations/api/schemas.py) as this client's own
/// type — never the backend's shape reused directly, same discipline the
/// backend itself follows toward `reality_engine`.
sealed class SimulationProgressEvent {
  const SimulationProgressEvent();
}

/// One Reality Engine agent starting or finishing.
///
/// `stage` stays an opaque string on purpose, same reasoning as the
/// backend's own `RealityEngineStageEvent`: this client has no fixed
/// opinion on which agents exist. A `stage` this build doesn't recognize
/// simply lights up no row (`SimulationStageGroup.forStageId` returns
/// `null`) rather than crashing the stream over an agent added later.
class SimulationStageProgress extends SimulationProgressEvent {
  const SimulationStageProgress({required this.stage, required this.status});

  final String stage;

  /// `"started"` | `"completed"`.
  final String status;
}

/// The stream's last line on a normal run: the same body
/// `POST .../simulations` returns synchronously.
class SimulationProgressResult extends SimulationProgressEvent {
  const SimulationProgressResult(this.simulation);

  final Simulation simulation;
}

/// Only reachable when the run fails *after* the stream's 200 already went
/// out (see the backend router's `_stream_lines` docstring). Ends the
/// stream: no stage or result line follows one of these.
class SimulationProgressError extends SimulationProgressEvent {
  const SimulationProgressError(this.message);

  final String message;
}

enum StageStatus { notStarted, inProgress, done }

/// The six rows docs/UX_DESIGN.md Pantalla 6 draws, each covering one or
/// more Reality Engine agents.
///
/// Stage ids stay per-agent on the wire — the backend's own
/// `PipelineStage` docstring is explicit that collapsing twelve agents into
/// six UI labels there would bake display copy into the engine. This is
/// where that collapsing is meant to happen instead.
enum SimulationStageGroup {
  understanding,
  goals,
  risks,
  scenarios,
  comparing,
  synthesizing;

  String get label => switch (this) {
    SimulationStageGroup.understanding => 'Comprendiendo',
    SimulationStageGroup.goals => 'Analizando objetivos',
    SimulationStageGroup.risks => 'Mapeando riesgos',
    SimulationStageGroup.scenarios => 'Generando escenarios',
    SimulationStageGroup.comparing => 'Comparando',
    SimulationStageGroup.synthesizing => 'Sintetizando',
  };

  /// The agent stage ids this row covers, in the pipeline's own run order
  /// (reality_engine/src/reality_engine/pipeline/domain/events.py's
  /// `PipelineStage`).
  ///
  /// Emotions and psychology have no row of their own in the spec's six —
  /// they read into "Mapeando riesgos" alongside the agent actually named
  /// that, since both feed how risk gets weighed rather than the objectives
  /// step that precedes them.
  List<String> get stageIds => switch (this) {
    SimulationStageGroup.understanding => const [
      'safety_gate',
      'comprehension',
      'summary',
    ],
    SimulationStageGroup.goals => const ['goals_extraction'],
    SimulationStageGroup.risks => const [
      'emotions',
      'psychology',
      'risk_analysis',
    ],
    SimulationStageGroup.scenarios => const ['scenario_generation'],
    SimulationStageGroup.comparing => const ['comparison', 'ranking'],
    SimulationStageGroup.synthesizing => const ['synthesis', 'memory'],
  };

  static SimulationStageGroup? forStageId(String stageId) {
    for (final group in SimulationStageGroup.values) {
      if (group.stageIds.contains(stageId)) return group;
    }
    return null;
  }
}

/// Accumulated stage progress while a stream is running — folds every
/// `SimulationStageProgress` event seen so far, keyed by the raw agent id.
class LiveSimulationProgress {
  const LiveSimulationProgress({this.stageStatuses = const {}});

  final Map<String, StageStatus> stageStatuses;

  LiveSimulationProgress withEvent(SimulationStageProgress event) {
    return LiveSimulationProgress(
      stageStatuses: {
        ...stageStatuses,
        event.stage: event.status == 'completed'
            ? StageStatus.done
            : StageStatus.inProgress,
      },
    );
  }

  /// A row is done only once every agent it covers is done, in progress as
  /// soon as any of them has started, and otherwise not started — the three
  /// states the wireframe's ✓ / ◐ / ○ symbols need.
  StageStatus statusFor(SimulationStageGroup group) {
    final statuses = group.stageIds.map(
      (id) => stageStatuses[id] ?? StageStatus.notStarted,
    );
    if (statuses.every((status) => status == StageStatus.done)) {
      return StageStatus.done;
    }
    if (statuses.any((status) => status != StageStatus.notStarted)) {
      return StageStatus.inProgress;
    }
    return StageStatus.notStarted;
  }
}
