import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:var_os_app/features/goals/domain/goals_repository.dart';
import 'package:var_os_app/features/goals/presentation/controllers/goals_controller.dart';
import 'package:var_os_app/features/goals/presentation/widgets/goal_pill.dart';
import 'package:var_os_app/features/goals/presentation/widgets/goals_profile_tab_content.dart';

import 'fakes.dart';

void main() {
  Future<void> pumpTab(
    WidgetTester tester, {
    required GoalsRepository repository,
  }) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [goalsRepositoryProvider.overrideWithValue(repository)],
        child: const MaterialApp(
          home: Scaffold(body: GoalsProfileTabContent()),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets('lists the goals the repository returns', (tester) async {
    await pumpTab(
      tester,
      repository: FakeGoalsRepository(
        goals: [
          testGoal(id: '1', name: 'Estabilidad financiera'),
          testGoal(id: '2', name: 'Salud/bienestar'),
        ],
      ),
    );

    expect(find.text('Estabilidad financiera'), findsOneWidget);
    expect(find.text('Salud/bienestar'), findsOneWidget);
  });

  testWidgets('only suggests seed goals the user does not already have', (
    tester,
  ) async {
    await pumpTab(
      tester,
      repository: FakeGoalsRepository(
        goals: [testGoal(id: '1', name: 'Estabilidad financiera')],
      ),
    );

    // Already owned, so it shows as a pill but not under "Sugeridos".
    expect(
      find.widgetWithText(ActionChip, 'Estabilidad financiera'),
      findsNothing,
    );
    expect(find.widgetWithText(ActionChip, 'Relaciones'), findsOneWidget);
  });

  testWidgets('adding a suggested goal creates it and re-lists', (
    tester,
  ) async {
    final repository = FakeGoalsRepository();
    await pumpTab(tester, repository: repository);

    await tester.tap(find.widgetWithText(ActionChip, 'Relaciones'));
    await tester.pumpAndSettle();

    expect(repository.createCalls.single.name, 'Relaciones');
    // Now owned: it moved out of the suggestions and into the pills.
    expect(find.widgetWithText(ActionChip, 'Relaciones'), findsNothing);
    expect(find.text('Relaciones'), findsOneWidget);
  });

  testWidgets('adding a custom goal from the text field', (tester) async {
    final repository = FakeGoalsRepository();
    await pumpTab(tester, repository: repository);

    await tester.enterText(find.byType(TextField), '  Tiempo con mi hija  ');
    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.pumpAndSettle();

    expect(repository.createCalls.single.name, 'Tiempo con mi hija');
  });

  testWidgets('an empty custom goal is ignored', (tester) async {
    final repository = FakeGoalsRepository();
    await pumpTab(tester, repository: repository);

    await tester.enterText(find.byType(TextField), '   ');
    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.pumpAndSettle();

    expect(repository.createCalls, isEmpty);
  });

  testWidgets('removing a goal deactivates it and drops it from the list', (
    tester,
  ) async {
    final repository = FakeGoalsRepository(
      goals: [testGoal(id: '1', name: 'Estabilidad financiera')],
    );
    await pumpTab(tester, repository: repository);

    await tester.tap(find.byIcon(Icons.close));
    await tester.pumpAndSettle();

    expect(repository.updateCalls.single.id, '1');
    expect(repository.updateCalls.single.isActive, isFalse);
    expect(find.byType(GoalPill), findsNothing);
    // It's a seed goal, so dropping it puts it back on offer under
    // "Sugeridos" — the only way back, since `GET /v1/goals` can no longer
    // list the deactivated row.
    expect(
      find.widgetWithText(ActionChip, 'Estabilidad financiera'),
      findsOneWidget,
    );
  });

  testWidgets('weight sliders stay hidden until "Ajuste avanzado" is opened', (
    tester,
  ) async {
    await pumpTab(
      tester,
      repository: FakeGoalsRepository(
        goals: [testGoal(id: '1', name: 'Carrera')],
      ),
    );

    expect(find.byType(Slider), findsNothing);

    await tester.tap(find.text('Ajuste avanzado'));
    await tester.pumpAndSettle();

    expect(find.byType(Slider), findsOneWidget);
  });

  testWidgets('releasing a weight slider commits exactly one update', (
    tester,
  ) async {
    final repository = FakeGoalsRepository(
      goals: [testGoal(id: '1', name: 'Carrera', defaultWeight: 50)],
    );
    await pumpTab(tester, repository: repository);
    await tester.tap(find.text('Ajuste avanzado'));
    await tester.pumpAndSettle();

    await tester.drag(find.byType(Slider), const Offset(60, 0));
    await tester.pumpAndSettle();

    expect(repository.updateCalls, hasLength(1));
    expect(repository.updateCalls.single.id, '1');
    expect(repository.updateCalls.single.weight, greaterThan(50));
  });

  testWidgets('shows an empty state when there are no goals', (tester) async {
    await pumpTab(tester, repository: FakeGoalsRepository());

    expect(find.textContaining('Aún no tienes objetivos'), findsOneWidget);
  });

  testWidgets('shows a retry affordance on failure', (tester) async {
    await pumpTab(
      tester,
      repository: FakeGoalsRepository(
        error: GoalsRepositoryError('network down'),
      ),
    );

    expect(find.text('No pudimos cargar tus objetivos.'), findsOneWidget);
    await tester.tap(find.text('Reintentar'));
    await tester.pumpAndSettle();
    expect(find.text('No pudimos cargar tus objetivos.'), findsOneWidget);
  });
}
