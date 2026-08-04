import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:var_os_app/features/decisions/domain/decisions_repository.dart';
import 'package:var_os_app/features/decisions/presentation/controllers/decisions_controller.dart';
import 'package:var_os_app/features/decisions/presentation/widgets/my_decisions_tab_content.dart';

import 'fakes.dart';

void main() {
  Future<void> pumpTab(
    WidgetTester tester, {
    required DecisionsRepository repository,
  }) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [decisionsRepositoryProvider.overrideWithValue(repository)],
        child: const MaterialApp(home: Scaffold(body: MyDecisionsTabContent())),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets('groups decisions into Activas / Completadas / Archivadas', (
    tester,
  ) async {
    await pumpTab(
      tester,
      repository: FakeDecisionsRepository(
        decisions: [
          testDecision(id: '1', title: 'En curso', status: 'clarifying'),
          testDecision(id: '2', title: 'Ya resuelta', status: 'completed'),
          testDecision(id: '3', title: 'Vieja', status: 'archived'),
        ],
      ),
    );

    expect(find.text('Activas'), findsOneWidget);
    expect(find.text('Completadas'), findsOneWidget);
    expect(find.text('Archivadas'), findsOneWidget);
    expect(find.text('En curso'), findsOneWidget);
    expect(find.text('Ya resuelta'), findsOneWidget);
    expect(find.text('Vieja'), findsOneWidget);
  });

  testWidgets('omits empty groups', (tester) async {
    await pumpTab(
      tester,
      repository: FakeDecisionsRepository(
        decisions: [testDecision(id: '1', title: 'Solo esta', status: 'draft')],
      ),
    );

    expect(find.text('Activas'), findsOneWidget);
    expect(find.text('Completadas'), findsNothing);
    expect(find.text('Archivadas'), findsNothing);
  });

  testWidgets('orders each group by most recently updated first', (
    tester,
  ) async {
    await pumpTab(
      tester,
      repository: FakeDecisionsRepository(
        decisions: [
          testDecision(
            id: '1',
            title: 'Más antigua',
            status: 'completed',
            updatedAt: DateTime.utc(2026, 1, 1),
          ),
          testDecision(
            id: '2',
            title: 'Más reciente',
            status: 'completed',
            updatedAt: DateTime.utc(2026, 6, 1),
          ),
        ],
      ),
    );

    final titles = tester
        .widgetList<Text>(find.byType(Text))
        .map((widget) => widget.data)
        .whereType<String>()
        .toList();
    expect(
      titles.indexOf('Más reciente'),
      lessThan(titles.indexOf('Más antigua')),
    );
  });

  testWidgets(
    'shows an empty-state message when there are no decisions at all',
    (tester) async {
      await pumpTab(tester, repository: FakeDecisionsRepository());

      expect(find.text('Aún no tienes decisiones.'), findsOneWidget);
    },
  );

  testWidgets('shows a retry affordance on failure', (tester) async {
    await pumpTab(
      tester,
      repository: FakeDecisionsRepository(
        error: DecisionsRepositoryError('network down'),
      ),
    );

    expect(find.text('No pudimos cargar tus decisiones.'), findsOneWidget);
    await tester.tap(find.text('Reintentar'));
    await tester.pumpAndSettle();
    expect(find.text('No pudimos cargar tus decisiones.'), findsOneWidget);
  });
}
