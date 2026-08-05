import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/routing/app_routes.dart';
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
                children: [
                  IconButton(
                    icon: const Icon(
                      Icons.settings_outlined,
                      color: VarColors.textSecondaryDark,
                    ),
                    tooltip: 'Ajustes',
                    // Pantalla 15 isn't built. Saying so beats an icon that
                    // silently does nothing — same treatment as the mic.
                    onPressed: () => ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('Ajustes llega en un próximo módulo.'),
                      ),
                    ),
                  ),
                  IconButton(
                    icon: const Icon(
                      Icons.person_outline,
                      color: VarColors.textSecondaryDark,
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
