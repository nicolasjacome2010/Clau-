import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:var_os_app/features/decisions/domain/decisions_repository.dart';
import 'package:var_os_app/features/decisions/presentation/controllers/decisions_controller.dart';
import 'package:var_os_app/features/home/presentation/screens/home_screen.dart';
import 'package:var_os_app/features/memory/presentation/controllers/bias_profile_controller.dart';

import '../decisions/fakes.dart';
import '../memory/fakes.dart';

void main() {
  Future<void> pumpHome(
    WidgetTester tester, {
    required DecisionsRepository repository,
  }) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          decisionsRepositoryProvider.overrideWithValue(repository),
          memoryRepositoryProvider.overrideWithValue(FakeMemoryRepository()),
        ],
        child: const MaterialApp(home: HomeScreen()),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets('shows active decisions returned by the repository', (
    tester,
  ) async {
    await pumpHome(
      tester,
      repository: FakeDecisionsRepository(
        decisions: [
          testDecision(
            id: '1',
            title: 'Oferta de trabajo Z',
            status: 'simulating',
          ),
          testDecision(
            id: '2',
            title: 'Mudarme a Lisboa',
            vertical: 'relocation',
            status: 'draft',
          ),
        ],
      ),
    );

    expect(find.text('Oferta de trabajo Z'), findsOneWidget);
    expect(find.text('Simulando'), findsOneWidget);
    expect(find.text('Mudarme a Lisboa'), findsOneWidget);
    expect(find.text('Borrador'), findsOneWidget);
  });

  testWidgets('filters out completed/archived decisions', (tester) async {
    await pumpHome(
      tester,
      repository: FakeDecisionsRepository(
        decisions: [
          testDecision(id: '1', title: 'Activa', status: 'clarifying'),
          testDecision(id: '2', title: 'Ya completada', status: 'completed'),
        ],
      ),
    );

    expect(find.text('Activa'), findsOneWidget);
    expect(find.text('Ya completada'), findsNothing);
  });

  testWidgets(
    'shows an empty-state message when there are no active decisions',
    (tester) async {
      await pumpHome(tester, repository: FakeDecisionsRepository());

      expect(find.text('Aún no tienes decisiones activas.'), findsOneWidget);
    },
  );

  testWidgets('shows a retry affordance on failure', (tester) async {
    await pumpHome(
      tester,
      repository: FakeDecisionsRepository(
        error: DecisionsRepositoryError('network down'),
      ),
    );

    expect(find.text('No pudimos cargar tus decisiones.'), findsOneWidget);
    expect(find.text('Reintentar'), findsOneWidget);

    await tester.tap(find.text('Reintentar'));
    await tester.pumpAndSettle();

    expect(find.text('No pudimos cargar tus decisiones.'), findsOneWidget);
  });

  testWidgets('switching to the Mis Decisiones tab shows the real list', (
    tester,
  ) async {
    await pumpHome(
      tester,
      repository: FakeDecisionsRepository(
        decisions: [
          testDecision(
            id: '1',
            title: 'Oferta de trabajo Z',
            status: 'simulating',
          ),
        ],
      ),
    );

    await tester.tap(find.text('Mis Decisiones'));
    await tester.pumpAndSettle();

    expect(find.text('Activas'), findsOneWidget);
    expect(find.text('Oferta de trabajo Z'), findsWidgets);
  });

  testWidgets('switching to the Memoria tab shows the real bias profile', (
    tester,
  ) async {
    await pumpHome(tester, repository: FakeDecisionsRepository());

    await tester.tap(find.text('Memoria'));
    await tester.pumpAndSettle();

    expect(find.text('Calibración'), findsOneWidget);
  });

  testWidgets('tapping the mic shows a coming-soon notice', (tester) async {
    await pumpHome(tester, repository: FakeDecisionsRepository());

    await tester.tap(find.byIcon(Icons.mic_none));
    await tester.pump();

    expect(
      find.text('La captura de voz llega en un próximo módulo.'),
      findsOneWidget,
    );
  });

  testWidgets('submitting the decision input shows a coming-soon notice', (
    tester,
  ) async {
    await pumpHome(tester, repository: FakeDecisionsRepository());

    await tester.enterText(find.byType(TextField), '¿Debo renunciar?');
    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.pump();

    expect(
      find.text('Guardar una decisión llega en un próximo módulo.'),
      findsOneWidget,
    );
  });

  testWidgets('uses a bottom NavigationBar on mobile widths', (tester) async {
    tester.view.physicalSize = const Size(400, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await pumpHome(tester, repository: FakeDecisionsRepository());

    expect(find.byType(NavigationBar), findsOneWidget);
    expect(find.byType(NavigationRail), findsNothing);
  });

  testWidgets('uses a NavigationRail on tablet+ widths', (tester) async {
    tester.view.physicalSize = const Size(900, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await pumpHome(tester, repository: FakeDecisionsRepository());

    expect(find.byType(NavigationRail), findsOneWidget);
    expect(find.byType(NavigationBar), findsNothing);
  });
}
