import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/routing/app_routes.dart';
import '../../../../design_system/var_palette.dart';
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
                style: VarTypography.display(20, context.varColors.textPrimary),
              ),
              Row(
                children: [
                  IconButton(
                    icon: Icon(
                      Icons.settings_outlined,
                      color: context.varColors.textSecondary,
                    ),
                    tooltip: 'Ajustes',
                    onPressed: () => context.push(AppRoutes.settings),
                  ),
                  IconButton(
                    icon: Icon(
                      Icons.person_outline,
                      color: context.varColors.textSecondary,
                    ),
                    tooltip: 'Suscripción',
                    onPressed: () => context.push(AppRoutes.subscription),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: VarSpacing.xl),
          Text(
            '¿Qué decisión estás enfrentando?',
            style: VarTypography.display(20, context.varColors.textPrimary),
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
