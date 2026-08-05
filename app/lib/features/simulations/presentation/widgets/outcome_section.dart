import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../design_system/var_colors.dart';
import '../../../../design_system/var_spacing.dart';
import '../../../../design_system/var_typography.dart';
import '../../domain/decision_outcome.dart';
import '../../domain/simulation.dart';
import '../controllers/decision_outcome_controller.dart';
import 'calibration_needle.dart';

/// Pantalla 11 — cierre de ciclo (docs/UX_DESIGN.md, docs/PRD.md CU8).
///
/// Lives at the bottom of the result screen rather than on a screen of its
/// own: the spec calls Pantalla 11 "detalle de decisión pasada + cierre de
/// ciclo", and the detail of a past decision is exactly what Pantallas 7+9
/// already render. Splitting it would mean re-fetching the same simulation
/// to show the same scenarios above the same prompt.
///
/// The CTA is an invitation, never a nag: docs/UX_DESIGN.md Pantalla 10 is
/// explicit that closing the loop "invita, no presiona" — so there is no
/// badge, no red dot, no dismissible modal, and skipping it costs nothing.
class OutcomeSection extends ConsumerStatefulWidget {
  const OutcomeSection({
    super.key,
    required this.decisionId,
    required this.scenarios,
  });

  final String decisionId;

  /// Used only to name the scenario Agente 12 matched. The client never
  /// picks a "closest" scenario itself.
  final List<SimulationScenario> scenarios;

  @override
  ConsumerState<OutcomeSection> createState() => _OutcomeSectionState();
}

class _OutcomeSectionState extends ConsumerState<OutcomeSection> {
  final _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final provider = decisionOutcomeControllerProvider(widget.decisionId);
    final asyncState = ref.watch(provider);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(VarSpacing.md),
      decoration: BoxDecoration(
        color: VarColors.bgSurfaceDark,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: VarColors.dividerDark),
      ),
      child: asyncState.when(
        data: (state) {
          final outcome = state.outcome;
          return outcome != null
              ? _Confirmation(outcome: outcome, scenarios: widget.scenarios)
              : _Prompt(
                  controller: _controller,
                  isSubmitting: state.isSubmitting,
                  errorMessage: state.errorMessage,
                  onSubmit: () =>
                      ref.read(provider.notifier).report(_controller.text),
                );
        },
        // Until `GET /v1/outcomes` answers, whether this loop is already
        // closed is unknown — and offering the prompt would be a guess that
        // could turn into a rejected request a second later.
        loading: () => const Center(
          child: Padding(
            padding: EdgeInsets.all(VarSpacing.md),
            child: CircularProgressIndicator(strokeWidth: 2),
          ),
        ),
        // A failed outcomes read must not hide the prompt: the loop is far
        // more likely open than closed, and `POST` answers 409 if it isn't.
        error: (error, _) => _Prompt(
          controller: _controller,
          isSubmitting: false,
          errorMessage: null,
          onSubmit: () => ref.read(provider.notifier).report(_controller.text),
        ),
      ),
    );
  }
}

class _Prompt extends StatelessWidget {
  const _Prompt({
    required this.controller,
    required this.isSubmitting,
    required this.errorMessage,
    required this.onSubmit,
  });

  final TextEditingController controller;
  final bool isSubmitting;
  final String? errorMessage;
  final VoidCallback onSubmit;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '¿Qué pasó realmente?',
          style: VarTypography.display(20, VarColors.textPrimaryDark),
        ),
        const SizedBox(height: VarSpacing.xs),
        Text(
          'Contarlo ajusta cómo el sistema te lee. Podés hacerlo cuando '
          'quieras — o no hacerlo.',
          style: VarTypography.body(12, VarColors.textSecondaryDark),
        ),
        const SizedBox(height: VarSpacing.md),
        TextField(
          controller: controller,
          enabled: !isSubmitting,
          maxLines: 3,
          minLines: 2,
          textInputAction: TextInputAction.newline,
          style: VarTypography.body(14, VarColors.textPrimaryDark),
          decoration: const InputDecoration(
            hintText: 'Acepté la oferta y a los 3 meses…',
          ),
        ),
        if (errorMessage != null) ...[
          const SizedBox(height: VarSpacing.sm),
          Text(
            errorMessage!,
            style: VarTypography.body(12, VarColors.signalLowDark),
          ),
        ],
        const SizedBox(height: VarSpacing.md),
        if (isSubmitting)
          Row(
            children: [
              const SizedBox(
                width: 16,
                height: 16,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
              const SizedBox(width: VarSpacing.sm),
              Text(
                'Calibrando…',
                style: VarTypography.body(12, VarColors.textSecondaryDark),
              ),
            ],
          )
        else
          ElevatedButton(
            onPressed: onSubmit,
            child: const Text('Registrar lo que pasó'),
          ),
      ],
    );
  }
}

class _Confirmation extends StatelessWidget {
  const _Confirmation({required this.outcome, required this.scenarios});

  final DecisionOutcome outcome;
  final List<SimulationScenario> scenarios;

  String? get _closestTitle {
    final id = outcome.closestScenarioId;
    if (id == null) return null;
    for (final scenario in scenarios) {
      if (scenario.id == id) return scenario.title;
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final closest = _closestTitle;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'El sistema aprendió algo',
          style: VarTypography.display(20, VarColors.textPrimaryDark),
        ),
        const SizedBox(height: VarSpacing.md),
        CalibrationNeedle(delta: outcome.calibrationDelta),
        const SizedBox(height: VarSpacing.md),
        if (outcome.matchedNoScenario)
          // docs/REALITY_ENGINE.md §2 treats "no scenario matched" as a
          // valuable result — a blind spot — so it is stated plainly
          // instead of being hidden behind a nearest-match guess.
          Text(
            'Lo que pasó no se parece a ninguno de los escenarios que '
            'generamos. Eso es un punto ciego nuestro, y queda registrado '
            'como tal.',
            style: VarTypography.body(14, VarColors.textPrimaryDark),
          )
        else if (closest != null)
          Text(
            'Lo más parecido fue: $closest',
            style: VarTypography.body(14, VarColors.textPrimaryDark),
          ),
        if (outcome.systemErrorsIdentified.isNotEmpty) ...[
          const SizedBox(height: VarSpacing.md),
          Text(
            'En qué se equivocó la simulación',
            style: VarTypography.body(
              12,
              VarColors.textSecondaryDark,
              weight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: VarSpacing.xs),
          for (final error in outcome.systemErrorsIdentified)
            Padding(
              padding: const EdgeInsets.only(bottom: 2),
              child: Text(
                '· $error',
                style: VarTypography.body(14, VarColors.textPrimaryDark),
              ),
            ),
        ],
      ],
    );
  }
}
