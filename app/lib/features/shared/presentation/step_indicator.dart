import 'package:flutter/material.dart';

import '../../../design_system/var_colors.dart';
import '../../../design_system/var_motion.dart';

/// The "● ○ ○" progress dots, shared by every multi-step flow — Onboarding
/// (docs/UX_DESIGN.md Pantalla 2) and Clarificación (Pantalla 5), which
/// both render the same affordance. Lives in `shared/` rather than inside
/// either feature precisely because neither owns it.
class StepIndicator extends StatelessWidget {
  const StepIndicator({
    super.key,
    required this.stepCount,
    required this.currentStep,
  });

  final int stepCount;
  final int currentStep;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: 'Paso ${currentStep + 1} de $stepCount',
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: List.generate(stepCount, (index) {
          final isActive = index == currentStep;
          return AnimatedContainer(
            duration: VarMotion.microMax,
            curve: VarMotion.enter,
            margin: const EdgeInsets.symmetric(horizontal: 4),
            width: isActive ? 20 : 8,
            height: 8,
            decoration: BoxDecoration(
              color: isActive ? VarColors.accentPrimary : VarColors.dividerDark,
              borderRadius: BorderRadius.circular(4),
            ),
          );
        }),
      ),
    );
  }
}
