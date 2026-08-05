import 'package:flutter/material.dart';

import '../../../../design_system/var_colors.dart';
import '../../../../design_system/var_spacing.dart';
import '../../../../design_system/var_typography.dart';
import '../../domain/billing_plan.dart';

/// One tier card (docs/UX_DESIGN.md Pantalla 14).
///
/// The spec's constraint is the design: "sin dark patterns (sin 'más
/// popular' artificial si no es honesto, sin temporizadores de urgencia
/// falsos)". So there is no highlighted recommendation, no countdown, no
/// crossed-out anchor price, and no visual hierarchy pushing one tier over
/// another — the only card that stands out is the one the user is already
/// on, which is information rather than persuasion.
class PlanCard extends StatelessWidget {
  const PlanCard({
    super.key,
    required this.plan,
    required this.isCurrent,
    required this.isBusy,
    required this.onSelect,
  });

  final BillingPlan plan;
  final bool isCurrent;
  final bool isBusy;
  final VoidCallback? onSelect;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: VarSpacing.md),
      padding: const EdgeInsets.all(VarSpacing.md),
      decoration: BoxDecoration(
        color: VarColors.bgSurfaceDark,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isCurrent ? VarColors.accentPrimary : VarColors.dividerDark,
          width: isCurrent ? 2 : 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  plan.name,
                  style: VarTypography.display(20, VarColors.textPrimaryDark),
                ),
              ),
              if (plan.priceLabel != null)
                Text(
                  plan.priceLabel!,
                  style: VarTypography.mono(16, VarColors.accentPrimary),
                ),
            ],
          ),
          const SizedBox(height: VarSpacing.xs),
          Text(
            plan.tagline,
            style: VarTypography.body(12, VarColors.textSecondaryDark),
          ),
          const SizedBox(height: VarSpacing.md),
          for (final feature in plan.features)
            Padding(
              padding: const EdgeInsets.only(bottom: 2),
              child: Text(
                '· $feature',
                style: VarTypography.body(14, VarColors.textPrimaryDark),
              ),
            ),
          const SizedBox(height: VarSpacing.md),
          if (isCurrent)
            Text(
              'Tu plan actual',
              style: VarTypography.body(
                12,
                VarColors.accentPrimary,
                weight: FontWeight.w600,
              ),
            )
          else if (plan.isPurchasable)
            ElevatedButton(
              onPressed: isBusy ? null : onSelect,
              child: Text('Elegir ${plan.name}'),
            )
          else if (plan.tier != 'free')
            // Said plainly rather than shown as a dead button: this build
            // has no Stripe price configured for the tier, so there is
            // nothing honest to charge.
            Text(
              'Este plan no está disponible para compra en esta versión.',
              style: VarTypography.body(12, VarColors.textSecondaryDark),
            ),
        ],
      ),
    );
  }
}
