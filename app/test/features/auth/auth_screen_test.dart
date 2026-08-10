import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:var_os_app/core/routing/app_routes.dart';
import 'package:var_os_app/features/auth/presentation/screens/auth_screen.dart';
import 'package:var_os_app/features/decisions/presentation/controllers/decisions_controller.dart';
import 'package:var_os_app/features/home/presentation/screens/home_screen.dart';
import 'package:var_os_app/features/memory/presentation/controllers/bias_profile_controller.dart';

import '../decisions/fakes.dart';
import '../memory/fakes.dart';

void main() {
  Future<void> pumpAuth(WidgetTester tester) async {
    final router = GoRouter(
      initialLocation: AppRoutes.auth,
      routes: [
        GoRoute(
          path: AppRoutes.auth,
          builder: (context, state) => const AuthScreen(),
        ),
        GoRoute(
          path: AppRoutes.home,
          builder: (context, state) => const HomeScreen(),
        ),
      ],
    );
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          decisionsRepositoryProvider.overrideWithValue(
            FakeDecisionsRepository(),
          ),
          memoryRepositoryProvider.overrideWithValue(FakeMemoryRepository()),
        ],
        child: MaterialApp.router(routerConfig: router),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets('continuing anonymously navigates straight to home', (
    tester,
  ) async {
    await pumpAuth(tester);

    await tester.tap(find.text('Probar una simulación primero'));
    await tester.pumpAndSettle();

    expect(find.byType(HomeScreen), findsOneWidget);
  });

  testWidgets(
    'submitting an invalid email shows an inline error, no navigation',
    (tester) async {
      await pumpAuth(tester);

      await tester.enterText(find.byType(TextField), 'not-an-email');
      await tester.tap(find.text('Continuar con email'));
      await tester.pumpAndSettle();

      expect(find.byType(AuthScreen), findsOneWidget);
      expect(find.textContaining('válido'), findsOneWidget);
    },
  );

  testWidgets('submitting a valid email navigates to home', (tester) async {
    await pumpAuth(tester);

    await tester.enterText(find.byType(TextField), 'alejandro@example.com');
    await tester.tap(find.text('Continuar con email'));
    await tester.pumpAndSettle();

    expect(find.byType(HomeScreen), findsOneWidget);
  });
}
