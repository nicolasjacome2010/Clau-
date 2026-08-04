import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_client.dart';
import '../../../decisions/presentation/controllers/decisions_controller.dart';
import '../../data/api_simulations_repository.dart';
import '../../domain/simulation.dart';
import '../../domain/simulations_repository.dart';

final simulationsRepositoryProvider = Provider<SimulationsRepository>(
  (ref) => ApiSimulationsRepository(ref.read(dioProvider)),
);

class DecisionSimulationState {
  const DecisionSimulationState({
    this.simulation,
    this.isRunning = false,
    this.errorMessage,
  });

  /// The most recent simulation for this decision, or `null` when the
  /// decision has never been simulated.
  final Simulation? simulation;
  final bool isRunning;
  final String? errorMessage;

  bool get hasResult => simulation != null;
}

/// Owns one decision's simulation: loads the latest on open, and runs a
/// new one on demand. Scoped per decision id via `.family`.
class DecisionSimulationController
    extends FamilyAsyncNotifier<DecisionSimulationState, String> {
  @override
  Future<DecisionSimulationState> build(String decisionId) async {
    final simulations = await ref
        .read(simulationsRepositoryProvider)
        .listForDecision(decisionId);
    return DecisionSimulationState(simulation: _mostRecent(simulations));
  }

  /// The backend returns simulations newest-first, but sorting here rather
  /// than trusting order keeps this correct if that ever changes.
  Simulation? _mostRecent(List<Simulation> simulations) {
    if (simulations.isEmpty) return null;
    final ordered = [...simulations]
      ..sort((a, b) => b.startedAt.compareTo(a.startedAt));
    return ordered.first;
  }

  Future<void> run() async {
    final current = state.valueOrNull ?? const DecisionSimulationState();
    if (current.isRunning) return;

    state = AsyncData(
      DecisionSimulationState(simulation: current.simulation, isRunning: true),
    );

    try {
      final simulation = await ref
          .read(simulationsRepositoryProvider)
          .runSimulation(arg);
      // Running a simulation moves the decision's own status
      // (draft → … → completed, see `RunSimulationUseCase`), so the shared
      // decisions list is stale until it re-reads.
      await ref.read(decisionsControllerProvider.notifier).refresh();
      state = AsyncData(DecisionSimulationState(simulation: simulation));
    } catch (error) {
      state = AsyncData(
        DecisionSimulationState(
          simulation: current.simulation,
          errorMessage: 'No pudimos completar la simulación.',
        ),
      );
    }
  }
}

final decisionSimulationControllerProvider =
    AsyncNotifierProvider.family<
      DecisionSimulationController,
      DecisionSimulationState,
      String
    >(DecisionSimulationController.new);
