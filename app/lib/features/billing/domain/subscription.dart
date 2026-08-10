/// The caller's current subscription, mirroring `SubscriptionResponse`
/// (backend/src/core_api/billing/api/schemas.py).
///
/// The backend answers with a synthetic free/active row when a user has no
/// Stripe subscription at all, so this is never null — "no subscription" is
/// spelled `tier == free`, not an absence.
class Subscription {
  const Subscription({
    required this.tier,
    required this.status,
    required this.currentPeriodEnd,
  });

  /// `free` | `pro` | `elite` | `team` (`SubscriptionTier` on the backend).
  final String tier;

  /// `active` | `past_due` | `canceled` | `trialing`.
  final String status;

  final DateTime? currentPeriodEnd;

  bool get isFree => tier == 'free';

  /// Whether there is anything for the Stripe Customer Portal to manage.
  /// A canceled or past-due paid plan still has a Stripe customer behind
  /// it, which is exactly when someone needs the portal most.
  bool get hasBillingRelationship => !isFree;
}
