import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/routing/app_routes.dart';
import '../../../../design_system/var_palette.dart';
import '../../../../design_system/var_spacing.dart';
import '../../../../design_system/var_typography.dart';
import '../../../decisions/domain/decision_ref.dart';
import '../../../decisions/domain/decision_summary.dart';
import '../../../decisions/presentation/widgets/decision_status_style.dart';

class ActiveDecisionCard extends StatelessWidget {
  const ActiveDecisionCard({super.key, required this.decision});

  final DecisionSummary decision;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: '${decision.title}, ${decisionStatusLabel(decision.status)}',
      child: Container(
        width: 160,
        margin: const EdgeInsets.only(right: VarSpacing.sm),
        // The surface color moves onto `Material` (rather than staying on the
        // inner `Container`'s decoration) so the tap ripple draws *on* the card
        // instead of on the Scaffold underneath it, where it would be hidden.
        child: Material(
          color: context.varColors.bgSurface,
          borderRadius: BorderRadius.circular(12),
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            onTap: () => context.push(
              AppRoutes.decisionResult,
              extra: DecisionRef(id: decision.id, title: decision.title),
            ),
            child: Container(
              padding: const EdgeInsets.symmetric(
                horizontal: VarSpacing.md,
                vertical: VarSpacing.sm,
              ),
              decoration: BoxDecoration(
                border: Border(
                  left: BorderSide(
                    color: decisionStatusColor(context, decision.status),
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
                      context.varColors.textPrimary,
                      weight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: VarSpacing.xs),
                  Text(
                    decisionStatusLabel(decision.status),
                    style: VarTypography.body(
                      12,
                      context.varColors.textSecondary,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
