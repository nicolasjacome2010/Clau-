import 'package:flutter/material.dart';

import '../../../../design_system/var_palette.dart';
import '../../../../design_system/var_motion.dart';
import '../../../../design_system/var_spacing.dart';
import '../../../../design_system/var_typography.dart';
import '../../domain/simulation.dart';
import 'score_bar.dart';

/// One scenario (docs/UX_DESIGN.md Pantalla 7). Tapping expands it to show
/// `assumptions` and the full narrative.
///
/// The top-ranked scenario gets an accent border, but every other scenario
/// stays fully visible and identically detailed — the spec is explicit:
/// "sin ocultar los demás — el usuario siempre ve el espacio completo de
/// opciones, coherente con 'el usuario decide'".
class ScenarioCard extends StatefulWidget {
  const ScenarioCard({super.key, required this.scenario});

  final SimulationScenario scenario;

  @override
  State<ScenarioCard> createState() => _ScenarioCardState();
}

class _ScenarioCardState extends State<ScenarioCard> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final scenario = widget.scenario;

    return Semantics(
      button: true,
      label:
          '${scenario.title}, probabilidad relativa '
          '${scenario.relativeProbability.round()}%',
      child: GestureDetector(
        onTap: () => setState(() => _expanded = !_expanded),
        child: AnimatedContainer(
          duration: VarMotion.screenTransitionMin,
          curve: VarMotion.enter,
          margin: const EdgeInsets.only(bottom: VarSpacing.md),
          padding: const EdgeInsets.all(VarSpacing.md),
          decoration: BoxDecoration(
            color: context.varColors.bgSurface,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: scenario.isTopRanked
                  ? context.varColors.accentPrimary
                  : context.varColors.divider,
              width: scenario.isTopRanked ? 2 : 1,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      scenario.title,
                      style: VarTypography.display(
                        16,
                        context.varColors.textPrimary,
                      ),
                    ),
                  ),
                  Text(
                    '${scenario.relativeProbability.round()}%',
                    style: VarTypography.mono(
                      16,
                      context.varColors.accentPrimary,
                    ),
                  ),
                ],
              ),
              Text(
                'Probabilidad relativa · ${scenario.timeHorizonMonths} meses',
                style: VarTypography.body(12, context.varColors.textSecondary),
              ),
              const SizedBox(height: VarSpacing.sm),
              Text(
                scenario.narrative,
                maxLines: _expanded ? null : 2,
                overflow: _expanded ? null : TextOverflow.ellipsis,
                style: VarTypography.body(14, context.varColors.textPrimary),
              ),
              const SizedBox(height: VarSpacing.md),
              for (final alignment in scenario.goalAlignmentScores)
                ScoreBar(
                  label: 'Alineación · ${alignment.goal}',
                  score: alignment.score,
                ),
              ScoreBar(
                label: 'Riesgo',
                score: scenario.riskScore,
                polarity: ScorePolarity.lowerIsBetter,
              ),
              ScoreBar(
                label: 'Reversibilidad',
                score: scenario.reversibilityScore,
              ),
              if (_expanded) ...[
                if (scenario.assumptions.isNotEmpty) ...[
                  const SizedBox(height: VarSpacing.sm),
                  Text(
                    'Supuestos',
                    style: VarTypography.body(
                      12,
                      context.varColors.textSecondary,
                      weight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: VarSpacing.xs),
                  for (final assumption in scenario.assumptions)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 2),
                      child: Text(
                        '· $assumption',
                        style: VarTypography.body(
                          12,
                          context.varColors.textSecondary,
                        ),
                      ),
                    ),
                ],
                for (final alignment in scenario.goalAlignmentScores)
                  if (alignment.justification.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: VarSpacing.xs),
                      child: Text(
                        '${alignment.goal}: ${alignment.justification}',
                        style: VarTypography.body(
                          12,
                          context.varColors.textSecondary,
                        ),
                      ),
                    ),
              ] else
                Text(
                  'Toca para ver supuestos',
                  style: VarTypography.body(
                    12,
                    context.varColors.textSecondary,
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
