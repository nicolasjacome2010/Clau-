import 'package:flutter/material.dart';

import '../../../../design_system/var_palette.dart';
import '../../../../design_system/var_spacing.dart';
import '../../../../design_system/var_typography.dart';

/// An existing goal, shown as a chip with a remove affordance
/// (docs/UX_DESIGN.md Pantalla 13: "chips editables de objetivos").
///
/// Labelled "Quitar", not a toggle: `GET /v1/goals` never returns
/// deactivated goals, so from the client's side this is one-way — see
/// `GoalsRepository`'s docstring.
class GoalPill extends StatelessWidget {
  const GoalPill({super.key, required this.name, required this.onRemove});

  final String name;
  final VoidCallback onRemove;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minHeight: VarSpacing.minTouchTarget),
      padding: const EdgeInsets.only(left: VarSpacing.md, right: VarSpacing.xs),
      decoration: BoxDecoration(
        color: context.varColors.bgSurface,
        borderRadius: BorderRadius.circular(VarSpacing.minTouchTarget / 2),
        border: Border.all(color: context.varColors.divider),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            name,
            style: VarTypography.body(14, context.varColors.textPrimary),
          ),
          Semantics(
            button: true,
            label: 'Quitar $name',
            child: IconButton(
              icon: Icon(
                Icons.close,
                size: 16,
                color: context.varColors.textSecondary,
              ),
              onPressed: onRemove,
              visualDensity: VisualDensity.compact,
            ),
          ),
        ],
      ),
    );
  }
}
