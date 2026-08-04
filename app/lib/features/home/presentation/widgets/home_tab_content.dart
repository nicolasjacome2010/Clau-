import 'package:flutter/material.dart';

import '../../../../design_system/var_colors.dart';
import '../../../../design_system/var_spacing.dart';
import '../../../../design_system/var_typography.dart';
import 'active_decisions_section.dart';
import 'decision_input_field.dart';

/// The "Home" destination's own content (docs/UX_DESIGN.md Pantalla 4):
/// top bar, dominant decision-input field, and the active-decisions list.
class HomeTabContent extends StatelessWidget {
  const HomeTabContent({super.key});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(VarSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'VAR OS',
                style: VarTypography.display(20, VarColors.textPrimaryDark),
              ),
              Row(
                children: const [
                  Icon(
                    Icons.settings_outlined,
                    color: VarColors.textSecondaryDark,
                  ),
                  SizedBox(width: VarSpacing.sm),
                  Icon(
                    Icons.person_outline,
                    color: VarColors.textSecondaryDark,
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: VarSpacing.xl),
          Text(
            '¿Qué decisión estás enfrentando?',
            style: VarTypography.display(20, VarColors.textPrimaryDark),
          ),
          const SizedBox(height: VarSpacing.md),
          const DecisionInputField(),
          const SizedBox(height: VarSpacing.xl),
          const ActiveDecisionsSection(),
        ],
      ),
    );
  }
}
