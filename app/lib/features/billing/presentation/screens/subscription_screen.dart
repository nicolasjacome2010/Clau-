import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../design_system/var_palette.dart';
import '../../../../design_system/var_spacing.dart';
import '../../../../design_system/var_typography.dart';
import '../../domain/subscription.dart';
import '../controllers/subscription_controller.dart';
import '../widgets/plan_card.dart';

/// Pantalla 14 — Suscripción / Facturación (docs/UX_DESIGN.md).
///
/// Payment itself never happens in this app: both buttons ask the backend
/// for a Stripe-hosted URL and hand it to the browser, so no card data ever
/// touches this process (docs/ARCHITECTURE.md §9).
class SubscriptionScreen extends ConsumerWidget {
  const SubscriptionScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncSubscription = ref.watch(subscriptionControllerProvider);

    return Scaffold(
      backgroundColor: context.varColors.bgPrimary,
      appBar: AppBar(
        backgroundColor: context.varColors.bgPrimary,
        title: Text(
          'Suscripción',
          style: VarTypography.body(16, context.varColors.textPrimary),
        ),
      ),
      body: SafeArea(
        child: asyncSubscription.when(
          data: (subscription) => _Body(subscription: subscription),
          loading: () =>
              const Center(child: CircularProgressIndicator(strokeWidth: 2)),
          error: (error, _) => Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'No pudimos cargar tu plan.',
                  style: VarTypography.body(12, context.varColors.signalLow),
                ),
                TextButton(
                  onPressed: () => ref
                      .read(subscriptionControllerProvider.notifier)
                      .refresh(),
                  child: const Text('Reintentar'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _Body extends ConsumerWidget {
  const _Body({required this.subscription});

  final Subscription subscription;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final action = ref.watch(billingActionControllerProvider);
    final plans = ref.watch(billingPlansProvider);

    return ListView(
      padding: const EdgeInsets.all(VarSpacing.lg),
      children: [
        _StatusNote(subscription: subscription),
        const SizedBox(height: VarSpacing.md),
        for (final plan in plans)
          PlanCard(
            plan: plan,
            isCurrent: plan.tier == subscription.tier,
            isBusy: action.isBusy,
            onSelect: () => ref
                .read(billingActionControllerProvider.notifier)
                .startCheckout(tier: plan.tier, priceId: plan.priceId!),
          ),
        if (subscription.hasBillingRelationship)
          OutlinedButton(
            onPressed: action.isBusy
                ? null
                : () => ref
                      .read(billingActionControllerProvider.notifier)
                      .openPortal(),
            child: const Text('Gestionar suscripción'),
          ),
        if (action.isBusy) ...[
          const SizedBox(height: VarSpacing.md),
          Row(
            children: [
              const SizedBox(
                width: 16,
                height: 16,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
              const SizedBox(width: VarSpacing.sm),
              Text(
                'Abriendo Stripe…',
                style: VarTypography.body(12, context.varColors.textSecondary),
              ),
            ],
          ),
        ],
        if (action.errorMessage != null) ...[
          const SizedBox(height: VarSpacing.md),
          Text(
            action.errorMessage!,
            style: VarTypography.body(12, context.varColors.signalLow),
          ),
        ],
        const SizedBox(height: VarSpacing.md),
        Text(
          'El pago se completa en Stripe, fuera de la app. Tu plan cambia '
          'cuando Stripe lo confirma.',
          style: VarTypography.body(12, context.varColors.textSecondary),
        ),
      ],
    );
  }
}

/// States what the subscription *is*, with no urgency and no upsell copy —
/// docs/UX_DESIGN.md Pantalla 14 rules those out explicitly.
class _StatusNote extends StatelessWidget {
  const _StatusNote({required this.subscription});

  final Subscription subscription;

  String get _text {
    final periodEnd = subscription.currentPeriodEnd;
    final until = periodEnd == null
        ? null
        : '${periodEnd.day}/${periodEnd.month}/${periodEnd.year}';

    switch (subscription.status) {
      case 'past_due':
        return 'Hay un pago pendiente. Podés resolverlo desde "Gestionar '
            'suscripción".';
      case 'canceled':
        return until == null
            ? 'Tu suscripción está cancelada.'
            : 'Tu suscripción está cancelada. Mantenés el acceso hasta el $until.';
      case 'trialing':
        return until == null
            ? 'Estás en período de prueba.'
            : 'Estás en período de prueba hasta el $until.';
      default:
        if (subscription.isFree) return 'Estás en el plan Free.';
        return until == null
            ? 'Tu plan está activo.'
            : 'Tu plan está activo. Se renueva el $until.';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Text(
      _text,
      style: VarTypography.body(14, context.varColors.textPrimary),
    );
  }
}
