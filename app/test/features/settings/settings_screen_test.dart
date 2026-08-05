import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:var_os_app/core/routing/app_routes.dart';
import 'package:var_os_app/design_system/var_theme.dart';
import 'package:var_os_app/features/billing/presentation/controllers/subscription_controller.dart';
import 'package:var_os_app/features/billing/presentation/screens/subscription_screen.dart';
import 'package:var_os_app/features/settings/domain/settings_repository.dart';
import 'package:var_os_app/features/settings/presentation/controllers/settings_controller.dart';
import 'package:var_os_app/features/settings/presentation/screens/settings_screen.dart';

import '../billing/fakes.dart';

class _FakeSettingsRepository implements SettingsRepository {
  _FakeSettingsRepository({this.stored = ThemeMode.system});

  ThemeMode stored;
  final List<ThemeMode> writes = [];

  @override
  Future<ThemeMode> readThemeMode() async => stored;

  @override
  Future<void> writeThemeMode(ThemeMode mode) async {
    writes.add(mode);
    stored = mode;
  }
}

void main() {
  Future<void> pumpSettings(
    WidgetTester tester, {
    required _FakeSettingsRepository settings,
  }) async {
    final router = GoRouter(
      initialLocation: AppRoutes.settings,
      routes: [
        GoRoute(
          path: AppRoutes.settings,
          builder: (context, state) => const SettingsScreen(),
        ),
        GoRoute(
          path: AppRoutes.subscription,
          builder: (context, state) => const SubscriptionScreen(),
        ),
      ],
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          settingsRepositoryProvider.overrideWithValue(settings),
          billingRepositoryProvider.overrideWithValue(FakeBillingRepository()),
        ],
        child: MaterialApp.router(
          theme: VarTheme.light,
          darkTheme: VarTheme.dark,
          routerConfig: router,
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets('offers the three appearance options the spec lists', (
    tester,
  ) async {
    await pumpSettings(tester, settings: _FakeSettingsRepository());

    expect(find.text('Como el sistema'), findsOneWidget);
    expect(find.text('Oscuro'), findsOneWidget);
    expect(find.text('Claro'), findsOneWidget);
    // The recommendation is copy, not a pre-made choice.
    expect(find.textContaining('Recomendamos el modo oscuro'), findsOneWidget);
  });

  testWidgets('starts from the stored preference, not a default', (
    tester,
  ) async {
    final settings = _FakeSettingsRepository(stored: ThemeMode.light);
    await pumpSettings(tester, settings: settings);

    final button = tester.widget<SegmentedButton<ThemeMode>>(
      find.byType(SegmentedButton<ThemeMode>),
    );
    expect(button.selected, {ThemeMode.light});
  });

  testWidgets('choosing an appearance persists it', (tester) async {
    final settings = _FakeSettingsRepository();
    await pumpSettings(tester, settings: settings);

    await tester.tap(find.text('Claro'));
    await tester.pumpAndSettle();

    expect(settings.writes, [ThemeMode.light]);
  });

  testWidgets('a setting with no backend says so, with the reason', (
    tester,
  ) async {
    // Better than a switch that toggles nothing: the user learns why.
    await pumpSettings(tester, settings: _FakeSettingsRepository());

    expect(find.text('Exportar mis datos'), findsOneWidget);
    expect(find.text('Borrar todo mi historial'), findsOneWidget);
    expect(find.text('Recordatorios de cierre de ciclo'), findsOneWidget);
    expect(
      find.textContaining('Falta el endpoint de exportación'),
      findsOneWidget,
    );

    // The last section is below the fold, and a lazy `ListView` hasn't
    // built it yet.
    await tester.scrollUntilVisible(find.text('Idioma'), 200);
    await tester.pumpAndSettle();

    expect(find.textContaining('solo en español por ahora'), findsOneWidget);
  });

  testWidgets('links to Suscripción', (tester) async {
    await pumpSettings(tester, settings: _FakeSettingsRepository());

    await tester.tap(find.text('Ver planes y facturación'));
    await tester.pumpAndSettle();

    expect(find.byType(SubscriptionScreen), findsOneWidget);
  });
}
