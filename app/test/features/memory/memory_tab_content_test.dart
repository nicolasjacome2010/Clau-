import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:var_os_app/features/memory/domain/memory_repository.dart';
import 'package:var_os_app/features/memory/domain/user_bias_profile.dart';
import 'package:var_os_app/features/memory/presentation/controllers/bias_profile_controller.dart';
import 'package:var_os_app/features/memory/presentation/widgets/memory_tab_content.dart';

import 'fakes.dart';

void main() {
  Future<void> pumpTab(
    WidgetTester tester, {
    required MemoryRepository repository,
  }) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [memoryRepositoryProvider.overrideWithValue(repository)],
        child: const MaterialApp(home: Scaffold(body: MemoryTabContent())),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets('shows detected bias patterns with evidence and score', (
    tester,
  ) async {
    await pumpTab(
      tester,
      repository: FakeMemoryRepository(
        profile: const UserBiasProfile(
          biases: [
            BiasObservation(
              bias:
                  'Sueles subestimar el tiempo de adaptación a cambios grandes',
              score: 0.72,
              occurrences: 3,
            ),
          ],
          calibrationScore: 15,
          updatedAt: null,
        ),
      ),
    );

    expect(
      find.text('Sueles subestimar el tiempo de adaptación a cambios grandes'),
      findsOneWidget,
    );
    expect(find.text('Visto en 3 decisiones pasadas'), findsOneWidget);
    expect(find.text('72%'), findsOneWidget);
  });

  testWidgets('singular evidence phrasing for a single occurrence', (
    tester,
  ) async {
    await pumpTab(
      tester,
      repository: FakeMemoryRepository(
        profile: const UserBiasProfile(
          biases: [
            BiasObservation(
              bias: 'Sesgo de confirmación',
              score: 0.5,
              occurrences: 1,
            ),
          ],
          calibrationScore: 0,
          updatedAt: null,
        ),
      ),
    );

    expect(find.text('Visto en 1 decisión pasada'), findsOneWidget);
  });

  testWidgets('shows an empty-state message when no patterns are detected', (
    tester,
  ) async {
    await pumpTab(tester, repository: FakeMemoryRepository());

    expect(
      find.text(
        'Aún no hemos detectado patrones — esto aparecerá después de tus primeras simulaciones.',
      ),
      findsOneWidget,
    );
  });

  testWidgets('shows the calibration score', (tester) async {
    await pumpTab(
      tester,
      repository: FakeMemoryRepository(
        profile: const UserBiasProfile(
          biases: [],
          calibrationScore: -42,
          updatedAt: null,
        ),
      ),
    );

    expect(find.text('Calibración'), findsOneWidget);
    expect(find.text('-42'), findsOneWidget);
  });

  testWidgets('shows a retry affordance on failure', (tester) async {
    await pumpTab(
      tester,
      repository: FakeMemoryRepository(
        error: MemoryRepositoryError('network down'),
      ),
    );

    expect(find.text('No pudimos cargar tu memoria.'), findsOneWidget);
    await tester.tap(find.text('Reintentar'));
    await tester.pumpAndSettle();
    expect(find.text('No pudimos cargar tu memoria.'), findsOneWidget);
  });

  testWidgets('export/delete buttons are visible', (tester) async {
    await pumpTab(tester, repository: FakeMemoryRepository());

    expect(find.text('Exportar mis datos'), findsOneWidget);
    expect(find.text('Borrar todo mi historial'), findsOneWidget);
  });

  testWidgets('tapping export shows a coming-soon notice', (tester) async {
    await pumpTab(tester, repository: FakeMemoryRepository());

    await tester.tap(find.text('Exportar mis datos'));
    await tester.pump();

    expect(
      find.text('Exportar mis datos llega en un próximo módulo.'),
      findsOneWidget,
    );
  });

  testWidgets('tapping delete-all shows a coming-soon notice', (tester) async {
    await pumpTab(tester, repository: FakeMemoryRepository());

    await tester.tap(find.text('Borrar todo mi historial'));
    await tester.pump();

    expect(
      find.text('Borrar todo mi historial llega en un próximo módulo.'),
      findsOneWidget,
    );
  });
}
