import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../design_system/var_palette.dart';
import '../../../../design_system/var_spacing.dart';
import '../../../../design_system/var_typography.dart';
import '../../domain/simulation.dart';
import '../../domain/simulation_progress.dart';
import '../controllers/decision_simulation_controller.dart';
import '../widgets/comparison_view.dart';
import '../widgets/live_simulation_view.dart';
import '../widgets/outcome_section.dart';
import '../widgets/safety_referral.dart';
import '../widgets/scenario_card.dart';
import '../widgets/synthesis_section.dart';

/// Pantallas 6 + 7 + 9 + 11 (docs/UX_DESIGN.md): a decision's simulated
/// scenarios, the final synthesis, the entry point that runs the simulation
/// — with Pantalla 6's real stage-by-stage progress while it's in flight,
/// via `LiveSimulationView` — and, once it has completed, the
/// close-the-loop prompt.
class DecisionResultScreen extends ConsumerWidget {
  const DecisionResultScreen({
    super.key,
    required this.decisionId,
    required this.title,
  });

  final String decisionId;
  final String title;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final provider = decisionSimulationControllerProvider(decisionId);
    final asyncState = ref.watch(provider);

    return Scaffold(
      backgroundColor: context.varColors.bgPrimary,
      appBar: AppBar(
        backgroundColor: context.varColors.bgPrimary,
        title: Text(
          title,
          style: VarTypography.body(16, context.varColors.textPrimary),
        ),
      ),
      body: SafeArea(
        child: asyncState.when(
          data: (state) => _Body(
            decisionId: decisionId,
            state: state,
            onRun: () => ref.read(provider.notifier).run(),
          ),
          loading: () =>
              const Center(child: CircularProgressIndicator(strokeWidth: 2)),
          error: (error, _) => _CenteredMessage(
            message: 'No pudimos cargar esta decisión.',
            actionLabel: 'Reintentar',
            onAction: () => ref.invalidate(provider),
          ),
        ),
      ),
    );
  }
}

class _Body extends StatelessWidget {
  const _Body({
    required this.decisionId,
    required this.state,
    required this.onRun,
  });

  final String decisionId;
  final DecisionSimulationState state;
  final VoidCallback onRun;

  @override
  Widget build(BuildContext context) {
    if (state.isRunning) {
      return LiveSimulationView(
        progress: state.liveProgress ?? const LiveSimulationProgress(),
      );
    }

    final simulation = state.simulation;
    if (simulation == null) {
      return _CenteredMessage(
        message: 'Esta decisión todavía no se ha simulado.',
        actionLabel: 'Simular ahora',
        onAction: onRun,
        errorMessage: state.errorMessage,
      );
    }

    // Checked before anything else: a halted run must never fall through to
    // scenario rendering, whatever else the payload happens to contain.
    if (simulation.safetyGate.requiresReferral) {
      return const SingleChildScrollView(
        padding: EdgeInsets.all(VarSpacing.lg),
        child: SafetyReferral(),
      );
    }

    if (simulation.isFailed || simulation.scenarios.isEmpty) {
      return _CenteredMessage(
        message: 'La simulación no pudo completarse.',
        actionLabel: 'Reintentar',
        onAction: onRun,
        errorMessage: state.errorMessage,
      );
    }

    return ListView(
      padding: const EdgeInsets.all(VarSpacing.lg),
      children: [
        _ResultViews(scenarios: simulation.rankedScenarios),
        if (simulation.synthesisText != null) ...[
          const SizedBox(height: VarSpacing.md),
          SynthesisSection(
            synthesis: simulation.synthesisText!,
            reflectiveQuestion: simulation.reflectiveQuestion,
          ),
        ],
        // Only offered against a *completed* simulation: `POST
        // /v1/decisions/{id}/outcome` answers 409 without one, and there is
        // nothing to calibrate against either way.
        if (simulation.isCompleted) ...[
          const SizedBox(height: VarSpacing.md),
          OutcomeSection(
            decisionId: decisionId,
            scenarios: simulation.scenarios,
          ),
        ],
        const SizedBox(height: VarSpacing.lg),
        if (state.errorMessage != null)
          Text(
            state.errorMessage!,
            style: VarTypography.body(12, context.varColors.signalLow),
          ),
        OutlinedButton(onPressed: onRun, child: const Text('Simular de nuevo')),
      ],
    );
  }
}

/// Pantallas 7 and 8 are two views of the same result, so they share one
/// screen and a toggle rather than a second route: the spec names them
/// "Resultado: Vista Escenarios" and "Resultado: Vista Comparación", and
/// re-fetching the same simulation to show the same numbers differently
/// would be work no user asked for.
///
/// The toggle only appears with two or more scenarios — there is nothing to
/// compare a single scenario against, and offering the view anyway would be
/// an empty promise.
class _ResultViews extends StatefulWidget {
  const _ResultViews({required this.scenarios});

  final List<SimulationScenario> scenarios;

  @override
  State<_ResultViews> createState() => _ResultViewsState();
}

class _ResultViewsState extends State<_ResultViews> {
  bool _comparing = false;

  @override
  Widget build(BuildContext context) {
    final canCompare = widget.scenarios.length > 1;
    final comparing = _comparing && canCompare;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                comparing ? 'Comparación' : 'Escenarios',
                style: VarTypography.display(20, context.varColors.textPrimary),
              ),
            ),
            if (canCompare)
              TextButton(
                onPressed: () => setState(() => _comparing = !comparing),
                child: Text(comparing ? 'Ver escenarios' : 'Comparar'),
              ),
          ],
        ),
        const SizedBox(height: VarSpacing.sm),
        if (comparing)
          ComparisonView(scenarios: widget.scenarios)
        else
          for (final scenario in widget.scenarios)
            ScenarioCard(scenario: scenario),
      ],
    );
  }
}

class _CenteredMessage extends StatelessWidget {
  const _CenteredMessage({
    required this.message,
    required this.actionLabel,
    required this.onAction,
    this.errorMessage,
  });

  final String message;
  final String actionLabel;
  final VoidCallback onAction;
  final String? errorMessage;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(VarSpacing.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              message,
              textAlign: TextAlign.center,
              style: VarTypography.body(16, context.varColors.textPrimary),
            ),
            if (errorMessage != null) ...[
              const SizedBox(height: VarSpacing.sm),
              Text(
                errorMessage!,
                textAlign: TextAlign.center,
                style: VarTypography.body(12, context.varColors.signalLow),
              ),
            ],
            const SizedBox(height: VarSpacing.md),
            ElevatedButton(onPressed: onAction, child: Text(actionLabel)),
          ],
        ),
      ),
    );
  }
}
