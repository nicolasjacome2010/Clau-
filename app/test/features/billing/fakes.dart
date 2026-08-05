import 'package:var_os_app/features/billing/domain/billing_repository.dart';
import 'package:var_os_app/features/billing/domain/subscription.dart';
import 'package:var_os_app/features/billing/domain/url_opener.dart';

class FakeBillingRepository implements BillingRepository {
  FakeBillingRepository({
    Subscription? subscription,
    this.subscriptionError,
    this.checkoutError,
    this.portalError,
    this.checkoutUrl = 'https://checkout.stripe.com/session',
    this.portalUrl = 'https://billing.stripe.com/portal',
  }) : _subscription =
           subscription ??
           const Subscription(
             tier: 'free',
             status: 'active',
             currentPeriodEnd: null,
           );

  Subscription _subscription;
  final BillingRepositoryError? subscriptionError;
  final BillingRepositoryError? checkoutError;
  final BillingRepositoryError? portalError;
  final String checkoutUrl;
  final String portalUrl;

  int subscriptionReads = 0;

  /// Every checkout session asked for, so a test can assert on exactly what
  /// would reach `POST /v1/billing/checkout-session`.
  final List<({String priceId, String successUrl, String cancelUrl})>
  checkoutCalls = [];
  final List<String> portalCalls = [];

  /// Simulates Stripe's webhook having landed: the plan only changes when
  /// the backend says it did, never because the client opened a URL.
  void serverSideUpgrade(Subscription subscription) {
    _subscription = subscription;
  }

  @override
  Future<Subscription> getSubscription() async {
    subscriptionReads += 1;
    if (subscriptionError != null) throw subscriptionError!;
    return _subscription;
  }

  @override
  Future<String> createCheckoutSession({
    required String priceId,
    required String successUrl,
    required String cancelUrl,
  }) async {
    checkoutCalls.add((
      priceId: priceId,
      successUrl: successUrl,
      cancelUrl: cancelUrl,
    ));
    if (checkoutError != null) throw checkoutError!;
    return checkoutUrl;
  }

  @override
  Future<String> createPortalSession({required String returnUrl}) async {
    portalCalls.add(returnUrl);
    if (portalError != null) throw portalError!;
    return portalUrl;
  }
}

class FakeUrlOpener implements UrlOpener {
  FakeUrlOpener({this.succeeds = true});

  final bool succeeds;
  final List<String> opened = [];

  @override
  Future<bool> open(String url) async {
    opened.add(url);
    return succeeds;
  }
}
