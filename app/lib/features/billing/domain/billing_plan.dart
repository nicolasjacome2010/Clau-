/// One tier in the comparison (docs/UX_DESIGN.md Pantalla 14: "comparación
/// de tiers (Free/Pro/Elite) en cards simples").
///
/// `features` is product copy and belongs here. `priceLabel` does **not**
/// belong here as a constant: what a plan costs is whatever Stripe charges,
/// and a number hardcoded in a shipped binary can drift from the price the
/// checkout actually bills — which is a consumer-protection problem, not a
/// styling nit. So the label is configured alongside the price id it
/// describes (`billing_config.dart`), and a plan with neither shows its
/// features without asserting a price. The right long-term fix is a
/// `GET /v1/billing/plans` that reads Stripe itself; until that exists this
/// is the version that can't lie.
class BillingPlan {
  const BillingPlan({
    required this.tier,
    required this.name,
    required this.tagline,
    required this.features,
    this.priceId,
    this.priceLabel,
  });

  final String tier;
  final String name;
  final String tagline;
  final List<String> features;

  /// `null` when this build has no Stripe price configured for the tier —
  /// the plan is still shown, but it can't be bought from here.
  final String? priceId;
  final String? priceLabel;

  bool get isPurchasable => priceId != null && priceId!.isNotEmpty;
}
