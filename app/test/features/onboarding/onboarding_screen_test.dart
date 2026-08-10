import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:var_os_app/core/routing/app_routes.dart';
import 'package:var_os_app/features/auth/presentation/screens/auth_screen.dart';
import 'package:var_os_app/features/onboarding/presentation/controllers/pending_goals_flusher.dart';
import 'package:var_os_app/features/onboarding/presentation/screens/onboarding_screen.dart';
import 'package:var_os_app/features/onboarding/presentation/widgets/goal_chip.dart';

import 'fakes.dart';

void main() {
  Future<void> pumpOnboarding(
    WidgetTester tester, {
    FakePendingGoalsStore? store,
  }) async {
    final router = GoRouter(
      initialLocation: AppRoutes.onboarding,
      routes: [
        GoRoute(
          path: AppRoutes.onboarding,
          builder: (context, state) => const OnboardingScreen(),
        ),
        GoRoute(
          path: AppRoutes.auth,
          builder: (context, state) => const AuthScreen(),
        ),
      ],
    );
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          pendingGoalsStoreProvider.overrideWithValue(
            store ?? FakePendingGoalsStore(),
          ),
        ],
        child: MaterialApp.router(routerConfig: router),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets('shows the first intro slide headline', (tester) async {
    await pumpOnboarding(tester);

    expect(find.textContaining('No predecimos tu futuro'), findsOneWidget);
  });

  testWidgets('advances through all 3 steps and reaches goal selection', (
    tester,
  ) async {
    await pumpOnboarding(tester);

    await tester.tap(find.text('Continuar →'));
    await tester.pumpAndSettle();
    expect(find.textContaining('Cada decisión abre líneas'), findsOneWidget);

    await tester.tap(find.text('Continuar →'));
    await tester.pumpAndSettle();
    expect(find.text('Estabilidad financiera'), findsOneWidget);
  });

  testWidgets('selecting a goal chip toggles its selected style', (
    tester,
  ) async {
    await pumpOnboarding(tester);
    await tester.tap(find.text('Continuar →'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Continuar →'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Estabilidad financiera'));
    await tester.pumpAndSettle();

    final chip = tester.widget<GoalChip>(
      find.widgetWithText(GoalChip, 'Estabilidad financiera'),
    );
    expect(chip.selected, isTrue);
  });

  testWidgets('completing the last step navigates to the auth screen', (
    tester,
  ) async {
    await pumpOnboarding(tester);
    await tester.tap(find.text('Continuar →'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Continuar →'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Continuar'));
    await tester.pumpAndSettle();

    expect(find.byType(AuthScreen), findsOneWidget);
  });

  testWidgets('the chosen goals are queued before leaving for auth', (
    tester,
  ) async {
    // The whole point of the queue: Pantalla 3 can send the user out of the
    // app (magic link), so the selection has to be on disk before we
    // navigate, not after we come back.
    final store = FakePendingGoalsStore();
    await pumpOnboarding(tester, store: store);
    await tester.tap(find.text('Continuar →'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Continuar →'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Salud/bienestar'));
    await tester.tap(find.text('Estabilidad financiera'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Continuar'));
    await tester.pumpAndSettle();

    // Stored in the spec's own chip order, not the tap order.
    expect(await store.read(), ['Estabilidad financiera', 'Salud/bienestar']);
  });

  testWidgets('skipping goal selection queues nothing at all', (tester) async {
    final store = FakePendingGoalsStore();
    await pumpOnboarding(tester, store: store);
    await tester.tap(find.text('Continuar →'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Continuar →'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Continuar'));
    await tester.pumpAndSettle();

    expect(await store.read(), isEmpty);
    expect(find.byType(AuthScreen), findsOneWidget);
  });
}
