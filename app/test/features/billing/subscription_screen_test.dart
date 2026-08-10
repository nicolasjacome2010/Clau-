import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:var_os_app/core/routing/app_routes.dart';
import 'package:var_os_app/features/billing/domain/billing_plan.dart';
import 'package:var_os_app/features/billing/domain/billing_repository.dart';
import 'package:var_os_app/features/billing/domain/subscription.dart';
import 'package:var_os_app/features/billing/presentation/controllers/subscription_controller.dart';
import 'package:var_os_app/features/billing/presentation/screens/subscription_screen.dart';

import 'fakes.dart';

const _returnUrl = 'https://varos.test/billing/done';

const _configuredPlans = [
  BillingPlan(
    tier: 'free',
    name: 'Free',
    tagline: 'Para probar.',
    priceLabel: 'Gratis',
    features: ['2 simulaciones por mes'],
  ),
  BillingPlan(
    tier: 'pro',
    name: 'Pro',
    tagline: 'Para decidir seguido.',
    priceId: 'price_pro',
    priceLabel: 'USD 19 / mes',
    features: ['Simulaciones ilimitadas'],
  ),
];

/// A build with no Stripe price for Pro — what a credential-less
/// environment actually produces.
const _unconfiguredPlans = [
  BillingPlan(
    tier: 'free',
    name: 'Free',
    tagline: 'Para probar.',
    priceLabel: 'Gratis',
    features: ['2 simulaciones por mes'],
  ),
  BillingPlan(
    tier: 'pro',
    name: 'Pro',
    tagline: 'Para decidir seguido.',
    features: ['Simulaciones ilimitadas'],
  ),
];

void main() {
  Future<void> pumpScreen(
    WidgetTester tester, {
    required FakeBillingRepository repository,
    FakeUrlOpener? opener,
    List<BillingPlan> plans = _configuredPlans,
  }) async {
    final router = GoRouter(
      initialLocation: AppRoutes.subscription,
      routes: [
        GoRoute(
          path: AppRoutes.subscription,
          builder: (context, state) => const SubscriptionScreen(),
        ),
      ],
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          billingRepositoryProvider.overrideWithValue(repository),
          urlOpenerProvider.overrideWithValue(opener ?? FakeUrlOpener()),
          billingPlansProvider.overrideWithValue(plans),
          billingReturnUrlProvider.overrideWithValue(_returnUrl),
        ],
        child: MaterialApp.router(routerConfig: router),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets('shows the tier comparison and marks the current plan', (
    tester,
  ) async {
    await pumpScreen(tester, repository: FakeBillingRepository());

    expect(find.text('Free'), findsOneWidget);
    expect(find.text('Pro'), findsOneWidget);
    expect(find.text('Estás en el plan Free.'), findsOneWidget);
    expect(find.text('Tu plan actual'), findsOneWidget);
    expect(find.text('Elegir Pro'), findsOneWidget);
  });

  testWidgets('carries no dark patterns', (tester) async {
    // docs/UX_DESIGN.md Pantalla 14 rules these out by name; asserting on
    // their absence is the only way that stays true as the copy evolves.
    await pumpScreen(tester, repository: FakeBillingRepository());

    expect(find.textContaining('popular'), findsNothing);
    expect(find.textContaining('Oferta'), findsNothing);
    expect(find.textContaining('quedan'), findsNothing);
    expect(find.textContaining('Solo por'), findsNothing);
  });

  testWidgets('a plan with no configured price is not offered for sale', (
    tester,
  ) async {
    await pumpScreen(
      tester,
      repository: FakeBillingRepository(),
      plans: _unconfiguredPlans,
    );

    expect(find.text('Pro'), findsOneWidget);
    expect(find.text('Elegir Pro'), findsNothing);
    expect(
      find.text('Este plan no está disponible para compra en esta versión.'),
      findsOneWidget,
    );
  });

  testWidgets('choosing a plan opens the Stripe checkout URL', (tester) async {
    final repository = FakeBillingRepository();
    final opener = FakeUrlOpener();
    await pumpScreen(tester, repository: repository, opener: opener);

    await tester.tap(find.text('Elegir Pro'));
    await tester.pumpAndSettle();

    expect(repository.checkoutCalls, hasLength(1));
    expect(repository.checkoutCalls.single.priceId, 'price_pro');
    expect(repository.checkoutCalls.single.successUrl, _returnUrl);
    expect(repository.checkoutCalls.single.cancelUrl, _returnUrl);
    expect(opener.opened, ['https://checkout.stripe.com/session']);
  });

  testWidgets('the plan only changes when the backend says it did', (
    tester,
  ) async {
    // Opening a checkout page is not a purchase: `Subscription` is a replica
    // of Stripe's own state, written only by the webhook handler.
    final repository = FakeBillingRepository();
    await pumpScreen(tester, repository: repository);

    await tester.tap(find.text('Elegir Pro'));
    await tester.pumpAndSettle();

    expect(find.text('Estás en el plan Free.'), findsOneWidget);
    expect(find.text('Elegir Pro'), findsOneWidget);

    // Now Stripe's webhook lands and the backend answers differently.
    repository.serverSideUpgrade(
      Subscription(
        tier: 'pro',
        status: 'active',
        currentPeriodEnd: DateTime.utc(2026, 9, 1),
      ),
    );
    await tester.tap(find.text('Elegir Pro'));
    await tester.pumpAndSettle();

    expect(
      find.text('Tu plan está activo. Se renueva el 1/9/2026.'),
      findsOneWidget,
    );
    expect(find.text('Elegir Pro'), findsNothing);
  });

  testWidgets('a browser that refuses to open is reported, not swallowed', (
    tester,
  ) async {
    await pumpScreen(
      tester,
      repository: FakeBillingRepository(),
      opener: FakeUrlOpener(succeeds: false),
    );

    await tester.tap(find.text('Elegir Pro'));
    await tester.pumpAndSettle();

    expect(
      find.text('No pudimos abrir la página de pago en tu navegador.'),
      findsOneWidget,
    );
  });

  testWidgets('a 503 says nothing was charged', (tester) async {
    await pumpScreen(
      tester,
      repository: FakeBillingRepository(
        checkoutError: BillingUnavailableError('down'),
      ),
    );

    await tester.tap(find.text('Elegir Pro'));
    await tester.pumpAndSettle();

    expect(find.textContaining('No se cobró nada'), findsOneWidget);
    // The plan the user is looking at survives a failed attempt.
    expect(find.text('Estás en el plan Free.'), findsOneWidget);
  });

  testWidgets('the portal is offered only with a paid plan behind it', (
    tester,
  ) async {
    await pumpScreen(tester, repository: FakeBillingRepository());

    expect(find.text('Gestionar suscripción'), findsNothing);
  });

  testWidgets('a paid plan can open the Stripe Customer Portal', (
    tester,
  ) async {
    final repository = FakeBillingRepository(
      subscription: const Subscription(
        tier: 'pro',
        status: 'active',
        currentPeriodEnd: null,
      ),
    );
    final opener = FakeUrlOpener();
    await pumpScreen(tester, repository: repository, opener: opener);

    await tester.tap(find.text('Gestionar suscripción'));
    await tester.pumpAndSettle();

    expect(repository.portalCalls, [_returnUrl]);
    expect(opener.opened, ['https://billing.stripe.com/portal']);
  });

  testWidgets('a canceled plan still reaches the portal', (tester) async {
    // Exactly when someone most needs it — a canceled subscription still has
    // a Stripe customer behind it.
    final repository = FakeBillingRepository(
      subscription: Subscription(
        tier: 'pro',
        status: 'canceled',
        currentPeriodEnd: DateTime.utc(2026, 9, 1),
      ),
    );
    await pumpScreen(tester, repository: repository);

    expect(
      find.text(
        'Tu suscripción está cancelada. Mantenés el acceso hasta el 1/9/2026.',
      ),
      findsOneWidget,
    );
    expect(find.text('Gestionar suscripción'), findsOneWidget);
  });

  testWidgets('a 404 from the portal is stated plainly', (tester) async {
    final repository = FakeBillingRepository(
      subscription: const Subscription(
        tier: 'pro',
        status: 'active',
        currentPeriodEnd: null,
      ),
      portalError: NoSubscriptionToManageError('none'),
    );
    await pumpScreen(tester, repository: repository);

    await tester.tap(find.text('Gestionar suscripción'));
    await tester.pumpAndSettle();

    expect(
      find.text('Todavía no tenés una suscripción que gestionar.'),
      findsOneWidget,
    );
  });

  testWidgets('a failed load offers a retry', (tester) async {
    await pumpScreen(
      tester,
      repository: FakeBillingRepository(
        subscriptionError: BillingRepositoryError('network down'),
      ),
    );

    expect(find.text('No pudimos cargar tu plan.'), findsOneWidget);
    expect(find.text('Reintentar'), findsOneWidget);
  });
}
