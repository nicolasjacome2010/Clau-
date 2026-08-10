import 'package:flutter/material.dart';

import '../../../../design_system/var_palette.dart';
import '../../../../design_system/var_spacing.dart';
import '../../../../design_system/var_typography.dart';

/// Pantalla 9 — Síntesis final (docs/UX_DESIGN.md).
///
/// The reflective question is set in Display type on purpose: the spec
/// calls it "el momento emocionalmente más importante de la sesión, se le
/// da espacio y jerarquía visual, no se trata como texto secundario".
class SynthesisSection extends StatelessWidget {
  const SynthesisSection({
    super.key,
    required this.synthesis,
    required this.reflectiveQuestion,
  });

  final String synthesis;
  final String? reflectiveQuestion;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(VarSpacing.md),
      decoration: BoxDecoration(
        color: context.varColors.bgElevated,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '✦ Síntesis',
            style: VarTypography.display(16, context.varColors.accentPrimary),
          ),
          const SizedBox(height: VarSpacing.sm),
          Text(
            synthesis,
            // AAA contrast on the most important text to read
            // (docs/UX_DESIGN.md §1.5) — hence primary, not secondary.
            style: VarTypography.body(16, context.varColors.textPrimary),
          ),
          if (reflectiveQuestion != null) ...[
            const SizedBox(height: VarSpacing.lg),
            Text(
              reflectiveQuestion!,
              style: VarTypography.display(20, context.varColors.textPrimary),
            ),
          ],
        ],
      ),
    );
  }
}
