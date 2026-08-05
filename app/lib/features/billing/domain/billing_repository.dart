import 'subscription.dart';

/// Port over the backend's `billing` bounded context
/// (backend/src/core_api/billing/api/router.py).
///
/// Checkout and the Customer Portal are both "give me a URL, then leave" —
/// the app never renders a payment form and never touches card data, which
/// is the entire point of using Stripe's hosted pages (docs/ARCHITECTURE.md
/// §9). Opening the URL is a separate concern (`UrlOpener`), so this port
/// stays about the API and not about the platform.
abstract class BillingRepository {
  Future<Subscription> getSubscription();

  Future<String> createCheckoutSession({
    required String priceId,
    required String successUrl,
    required String cancelUrl,
  });

  Future<String> createPortalSession({required String returnUrl});
}

class BillingRepositoryError implements Exception {
  BillingRepositoryError(this.message);

  final String message;

  @override
  String toString() => 'BillingRepositoryError: $message';
}

/// The backend's 404 on `POST /v1/billing/portal-session`: this user has no
/// Stripe customer yet, so there is nothing to manage. A distinct type
/// because "todavía no tenés una suscripción" is a different sentence from
/// "algo salió mal".
class NoSubscriptionToManageError extends BillingRepositoryError {
  NoSubscriptionToManageError(super.message);
}

/// The backend's 503: Stripe is unreachable, or this deployment has no
/// Stripe keys configured at all (it fails closed rather than open). Either
/// way nothing was charged and retrying is safe.
class BillingUnavailableError extends BillingRepositoryError {
  BillingUnavailableError(super.message);
}
