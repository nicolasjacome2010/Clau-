import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../design_system/var_colors.dart';
import '../../../../design_system/var_spacing.dart';
import '../../../../design_system/var_typography.dart';
import '../controllers/decision_simulation_controller.dart';
import '../widgets/running_indicator.dart';
import '../widgets/safety_referral.dart';
import '../widgets/scenario_card.dart';
import '../widgets/synthesis_section.dart';

/// Pantallas 7 + 9 (docs/UX_DESIGN.md): a decision's simulated scenarios
/// and the final synthesis, plus the entry point that runs the simulation.
///
/// Pantalla 6 ("Simulación en vivo", the stage-by-stage streaming view) is
/// deliberately not here: it needs a pipeline-progress WebSocket the
/// backend doesn't expose (docs/ARCHITECTURE.md §2.2 describes it as
/// future work). While the request is in flight this shows an honest
/// indeterminate wait — never a synthetic progress bar, which the spec
/// warns "rompería confianza si se estanca".
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
      backgroundColor: VarColors.bgPrimaryDark,
      appBar: AppBar(
        backgroundColor: VarColors.bgPrimaryDark,
        title: Text(
          title,
          style: VarTypography.body(16, VarColors.textPrimaryDark),
        ),
      ),
      body: SafeArea(
        child: asyncState.when(
          data: (state) => _Body(
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
  const _Body({required this.state, required this.onRun});

  final DecisionSimulationState state;
  final VoidCallback onRun;

  @override
  Widget build(BuildContext context) {
    if (state.isRunning) return const RunningIndicator();

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
        Text(
          'Escenarios',
          style: VarTypography.display(20, VarColors.textPrimaryDark),
        ),
        const SizedBox(height: VarSpacing.sm),
        for (final scenario in simulation.rankedScenarios)
          ScenarioCard(scenario: scenario),
        if (simulation.synthesisText != null) ...[
          const SizedBox(height: VarSpacing.md),
          SynthesisSection(
            synthesis: simulation.synthesisText!,
            reflectiveQuestion: simulation.reflectiveQuestion,
          ),
        ],
        const SizedBox(height: VarSpacing.lg),
        if (state.errorMessage != null)
          Text(
            state.errorMessage!,
            style: VarTypography.body(12, VarColors.signalLowDark),
          ),
        OutlinedButton(onPressed: onRun, child: const Text('Simular de nuevo')),
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
              style: VarTypography.body(16, VarColors.textPrimaryDark),
            ),
            if (errorMessage != null) ...[
              const SizedBox(height: VarSpacing.sm),
              Text(
                errorMessage!,
                textAlign: TextAlign.center,
                style: VarTypography.body(12, VarColors.signalLowDark),
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
