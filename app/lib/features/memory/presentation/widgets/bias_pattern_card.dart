import 'package:flutter/material.dart';

import '../../../../design_system/var_palette.dart';
import '../../../../design_system/var_spacing.dart';
import '../../../../design_system/var_typography.dart';
import '../../domain/user_bias_profile.dart';

/// A detected pattern card (docs/UX_DESIGN.md Pantalla 12), e.g. "Sueles
/// subestimar el tiempo que necesitas para adaptarte a cambios grandes",
/// with evidence: "visto en 3 decisiones pasadas".
class BiasPatternCard extends StatelessWidget {
  const BiasPatternCard({super.key, required this.observation});

  final BiasObservation observation;

  @override
  Widget build(BuildContext context) {
    final percentage = (observation.score * 100).round();
    final evidence = observation.occurrences == 1
        ? 'Visto en 1 decisión pasada'
        : 'Visto en ${observation.occurrences} decisiones pasadas';

    return Semantics(
      label: '${observation.bias}. $evidence. Confianza $percentage%.',
      child: Container(
        width: double.infinity,
        margin: const EdgeInsets.only(bottom: VarSpacing.sm),
        padding: const EdgeInsets.all(VarSpacing.md),
        decoration: BoxDecoration(
          color: context.varColors.bgSurface,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              observation.bias,
              style: VarTypography.body(
                14,
                context.varColors.textPrimary,
                weight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: VarSpacing.xs),
            Text(
              evidence,
              style: VarTypography.body(12, context.varColors.textSecondary),
            ),
            const SizedBox(height: VarSpacing.sm),
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: observation.score.clamp(0.0, 1.0),
                minHeight: 6,
                backgroundColor: context.varColors.divider,
                valueColor: AlwaysStoppedAnimation(
                  context.varColors.accentPrimary,
                ),
              ),
            ),
            const SizedBox(height: VarSpacing.xs),
            Text(
              '$percentage%',
              style: VarTypography.mono(12, context.varColors.textSecondary),
            ),
          ],
        ),
      ),
    );
  }
}
