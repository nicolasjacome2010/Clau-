import 'package:flutter/material.dart';

import '../../../../design_system/var_colors.dart';
import '../../../../design_system/var_spacing.dart';
import '../../../../design_system/var_typography.dart';
import '../../domain/decision_summary.dart';
import 'decision_status_style.dart';

class ActiveDecisionCard extends StatelessWidget {
  const ActiveDecisionCard({super.key, required this.decision});

  final DecisionSummary decision;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: '${decision.title}, ${decisionStatusLabel(decision.status)}',
      child: Container(
        width: 160,
        padding: const EdgeInsets.symmetric(
          horizontal: VarSpacing.md,
          vertical: VarSpacing.sm,
        ),
        margin: const EdgeInsets.only(right: VarSpacing.sm),
        decoration: BoxDecoration(
          color: VarColors.bgSurfaceDark,
          borderRadius: BorderRadius.circular(12),
          border: Border(
            left: BorderSide(
              color: decisionStatusColor(decision.status),
              width: 3,
            ),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.center,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              decision.title,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: VarTypography.body(
                14,
                VarColors.textPrimaryDark,
                weight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: VarSpacing.xs),
            Text(
              decisionStatusLabel(decision.status),
              style: VarTypography.body(12, VarColors.textSecondaryDark),
            ),
          ],
        ),
      ),
    );
  }
}
