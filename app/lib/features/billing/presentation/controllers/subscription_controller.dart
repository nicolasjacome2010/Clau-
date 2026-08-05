import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_client.dart';
import '../../data/api_billing_repository.dart';
import '../../data/billing_config.dart';
import '../../data/url_launcher_opener.dart';
import '../../domain/billing_plan.dart';
import '../../domain/billing_repository.dart';
import '../../domain/subscription.dart';
import '../../domain/url_opener.dart';

final billingRepositoryProvider = Provider<BillingRepository>(
  (ref) => ApiBillingRepository(ref.read(dioProvider)),
);

final urlOpenerProvider = Provider<UrlOpener>(
  (ref) => const UrlLauncherOpener(),
);

/// Build-time configuration behind providers rather than read straight from
/// `billing_config.dart` at the call site: `String.fromEnvironment` is fixed
/// at compile time, so a test could otherwise never exercise a configured
/// build. Overriding these is also how a future flavor could ship different
/// plans without touching the screen.
final billingPlansProvider = Provider<List<BillingPlan>>(
  (ref) => billingPlans(),
);

final billingReturnUrlProvider = Provider<String>((ref) => billingReturnUrl);

/// The caller's current plan (`GET /v1/billing/subscription`).
///
/// Read from the backend rather than assumed: `Subscription` is a replica of
/// Stripe's own state, written only by the webhook handler, so the app can
/// no more infer a tier from a successful checkout than it can from a
/// hopeful guess — the plan changes when Stripe says it did.
class SubscriptionController extends AsyncNotifier<Subscription> {
  @override
  Future<Subscription> build() => _fetch();

  Future<void> refresh() async {
    state = const AsyncLoading<Subscription>().copyWithPrevious(state);
    state = await AsyncValue.guard(_fetch);
  }

  Future<Subscription> _fetch() =>
      ref.read(billingRepositoryProvider).getSubscription();
}

final subscriptionControllerProvider =
    AsyncNotifierProvider<SubscriptionController, Subscription>(
      SubscriptionController.new,
    );

/// What the screen is doing right now, separate from what the subscription
/// *is* — a failed checkout attempt must not blank out the plan the user is
/// looking at.
class BillingActionState {
  const BillingActionState({this.inFlightTier, this.errorMessage});

  /// The tier whose button is waiting on Stripe, or `'portal'` for the
  /// Customer Portal — enough to disable exactly one button, not all of
  /// them.
  final String? inFlightTier;
  final String? errorMessage;

  bool get isBusy => inFlightTier != null;
}

class BillingActionController extends Notifier<BillingActionState> {
  @override
  BillingActionState build() => const BillingActionState();

  Future<void> startCheckout({required String tier, required String priceId}) {
    final returnUrl = ref.read(billingReturnUrlProvider);
    return _run(tier, () {
      return ref
          .read(billingRepositoryProvider)
          .createCheckoutSession(
            priceId: priceId,
            // Stripe sends the user back to the same place either way: the
            // app can't trust a "success" redirect anyway — only the webhook
            // decides what the user actually has.
            successUrl: returnUrl,
            cancelUrl: returnUrl,
          );
    });
  }

  Future<void> openPortal() {
    final returnUrl = ref.read(billingReturnUrlProvider);
    return _run('portal', () {
      return ref
          .read(billingRepositoryProvider)
          .createPortalSession(returnUrl: returnUrl);
    });
  }

  Future<void> _run(
    String tier,
    Future<String> Function() createSession,
  ) async {
    if (state.isBusy) return;
    state = BillingActionState(inFlightTier: tier);

    try {
      final url = await createSession();
      final opened = await ref.read(urlOpenerProvider).open(url);
      if (!opened) {
        // The session was created but the platform wouldn't open it. Saying
        // so beats a button that silently does nothing.
        state = const BillingActionState(
          errorMessage: 'No pudimos abrir la página de pago en tu navegador.',
        );
        return;
      }
      // The tier only changes when Stripe's webhook says so, so re-read
      // rather than assume the user completed the checkout — they may well
      // have closed the tab.
      await ref.read(subscriptionControllerProvider.notifier).refresh();
      state = const BillingActionState();
    } on NoSubscriptionToManageError {
      state = const BillingActionState(
        errorMessage: 'Todavía no tenés una suscripción que gestionar.',
      );
    } on BillingUnavailableError {
      state = const BillingActionState(
        errorMessage:
            'El sistema de pagos no está disponible ahora mismo. No se '
            'cobró nada — podés volver a intentarlo.',
      );
    } catch (error) {
      state = const BillingActionState(
        errorMessage: 'No pudimos continuar con el pago.',
      );
    }
  }
}

final billingActionControllerProvider =
    NotifierProvider<BillingActionController, BillingActionState>(
      BillingActionController.new,
    );
