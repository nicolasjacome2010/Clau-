import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:var_os_app/core/routing/app_routes.dart';
import 'package:var_os_app/features/onboarding/presentation/screens/onboarding_screen.dart';
import 'package:var_os_app/features/splash/presentation/splash_screen.dart';

void main() {
  Widget wrap(GoRouter router) =>
      ProviderScope(child: MaterialApp.router(routerConfig: router));

  testWidgets('navigates to onboarding once the 600ms animation completes', (
    tester,
  ) async {
    final router = GoRouter(
      initialLocation: AppRoutes.splash,
      routes: [
        GoRoute(
          path: AppRoutes.splash,
          builder: (context, state) => const SplashScreen(),
        ),
        GoRoute(
          path: AppRoutes.onboarding,
          builder: (context, state) => const OnboardingScreen(),
        ),
      ],
    );

    await tester.pumpWidget(wrap(router));
    expect(find.text('VAR OS'), findsOneWidget);

    await tester.pump(const Duration(milliseconds: 601));
    await tester.pumpAndSettle();

    expect(find.byType(OnboardingScreen), findsOneWidget);
  });
}
