import 'package:flutter/material.dart';

import '../../../../design_system/var_colors.dart';
import '../../../../design_system/var_palette.dart';
import '../../../../design_system/var_spacing.dart';
import '../../../../design_system/var_typography.dart';

/// A single value-proposition slide (Pasos 1-2 of Pantalla 2,
/// docs/UX_DESIGN.md). The abstract illustration is a placeholder shape,
/// not a real asset — the real "líneas temporales" illustration is a
/// design-asset deliverable outside this pass's scope.
class IntroSlide extends StatelessWidget {
  const IntroSlide({super.key, required this.headline});

  final String headline;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: VarSpacing.xl),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            width: 96,
            height: 96,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: LinearGradient(colors: VarColors.accentGradient),
            ),
          ),
          const SizedBox(height: VarSpacing.xxl),
          Text(
            headline,
            textAlign: TextAlign.center,
            style: VarTypography.display(25, context.varColors.textPrimary),
          ),
        ],
      ),
    );
  }
}
