/// Stripe price ids and the URLs Stripe sends the user back to, injected at
/// build time like every other environment value (docs/ARCHITECTURE.md §3).
///
/// ```
/// flutter run \
///   --dart-define=STRIPE_PRICE_PRO=price_123 \
///   --dart-define=STRIPE_PRICE_PRO_LABEL='USD 19 / mes' \
///   --dart-define=STRIPE_PRICE_ELITE=price_456 \
///   --dart-define=STRIPE_PRICE_ELITE_LABEL='USD 49 / mes' \
///   --dart-define=BILLING_RETURN_URL=https://tu-dominio/billing/done
/// ```
///
/// Each label sits next to the id it describes so the two are configured in
/// one place and can't drift apart — see `BillingPlan` for why the price is
/// not a constant in the source.
library;

import '../domain/billing_plan.dart';

const String stripePricePro = String.fromEnvironment('STRIPE_PRICE_PRO');
const String stripePriceProLabel = String.fromEnvironment(
  'STRIPE_PRICE_PRO_LABEL',
);
const String stripePriceElite = String.fromEnvironment('STRIPE_PRICE_ELITE');
const String stripePriceEliteLabel = String.fromEnvironment(
  'STRIPE_PRICE_ELITE_LABEL',
);

/// Where Stripe returns the user after checkout or after the portal.
///
/// Stripe requires an absolute URL, and this app has no registered deep
/// link scheme yet (the same gap that blocks Pantalla 3's OAuth buttons), so
/// it is configured rather than derived. Without it nothing is purchasable
/// from this build — see `isCheckoutConfigured`.
const String billingReturnUrl = String.fromEnvironment('BILLING_RETURN_URL');

const bool isCheckoutConfigured = billingReturnUrl != '';

String? _idOrNull(String value) => value.isEmpty ? null : value;

/// The tier comparison. Features are product copy (docs/PRD.md §12); prices
/// come from configuration, so an unconfigured build shows what each plan
/// includes without claiming what it costs.
List<BillingPlan> billingPlans() {
  return [
    const BillingPlan(
      tier: 'free',
      name: 'Free',
      tagline: 'Para probar el sistema con decisiones reales.',
      // The one price that can't drift, because it isn't charged.
      priceLabel: 'Gratis',
      features: [
        '2 simulaciones completas por mes',
        '3 escenarios por simulación',
        'Sin memoria de largo plazo',
      ],
    ),
    BillingPlan(
      tier: 'pro',
      name: 'Pro',
      tagline: 'Para quien decide seguido y quiere que el sistema aprenda.',
      priceId: isCheckoutConfigured ? _idOrNull(stripePricePro) : null,
      priceLabel: _idOrNull(stripePriceProLabel),
      features: [
        'Simulaciones ilimitadas',
        'Hasta 5 escenarios por simulación',
        'Memoria y calibración entre decisiones',
        'Export PDF',
      ],
    ),
    BillingPlan(
      tier: 'elite',
      name: 'Elite',
      tagline: 'Para decisiones de negocio con más en juego.',
      priceId: isCheckoutConfigured ? _idOrNull(stripePriceElite) : null,
      priceLabel: _idOrNull(stripePriceEliteLabel),
      features: [
        'Todo lo de Pro',
        'Agente de negocio avanzado',
        'Prioridad de cómputo',
        'Onboarding con soporte humano',
      ],
    ),
  ];
}
