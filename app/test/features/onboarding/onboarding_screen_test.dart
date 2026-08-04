import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:var_os_app/core/routing/app_routes.dart';
import 'package:var_os_app/features/auth/presentation/screens/auth_screen.dart';
import 'package:var_os_app/features/onboarding/presentation/screens/onboarding_screen.dart';
import 'package:var_os_app/features/onboarding/presentation/widgets/goal_chip.dart';

void main() {
  Future<void> pumpOnboarding(WidgetTester tester) async {
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
      ProviderScope(child: MaterialApp.router(routerConfig: router)),
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
}
