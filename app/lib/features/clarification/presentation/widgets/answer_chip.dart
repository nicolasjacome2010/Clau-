import 'package:flutter/material.dart';

import '../../../../design_system/var_colors.dart';
import '../../../../design_system/var_motion.dart';
import '../../../../design_system/var_spacing.dart';
import '../../../../design_system/var_typography.dart';

/// A quick-reply chip for Pantalla 5.
///
/// Deliberately not `onboarding`'s `GoalChip`: that one is a persistent
/// multi-select toggle (tap to add/remove from a set), this one is
/// fire-and-advance (tap answers the question and moves on, with no
/// selected state to render). They look alike only because both pull from
/// the same `design_system` tokens — which is where visual consistency is
/// supposed to live, so sharing the widget itself would couple two
/// unrelated interactions.
class AnswerChip extends StatelessWidget {
  const AnswerChip({super.key, required this.label, required this.onTap});

  final String label;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: label,
      child: GestureDetector(
        onTap: onTap,
        child: AnimatedContainer(
          duration: VarMotion.microMax,
          curve: VarMotion.enter,
          constraints: const BoxConstraints(
            minHeight: VarSpacing.minTouchTarget,
          ),
          padding: const EdgeInsets.symmetric(
            horizontal: VarSpacing.md,
            vertical: VarSpacing.sm,
          ),
          decoration: BoxDecoration(
            color: VarColors.bgSurfaceDark,
            borderRadius: BorderRadius.circular(VarSpacing.minTouchTarget / 2),
            border: Border.all(color: VarColors.dividerDark),
          ),
          alignment: Alignment.center,
          child: Text(
            label,
            style: VarTypography.body(14, VarColors.textPrimaryDark),
          ),
        ),
      ),
    );
  }
}
