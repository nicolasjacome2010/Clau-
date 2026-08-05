import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:var_os_app/core/routing/app_routes.dart';
import 'package:var_os_app/features/decisions/domain/decision_ref.dart';
import 'package:var_os_app/features/decisions/domain/decisions_repository.dart';
import 'package:var_os_app/features/decisions/presentation/controllers/decisions_controller.dart';
import 'package:var_os_app/features/decisions/presentation/widgets/my_decisions_tab_content.dart';
import 'package:var_os_app/features/simulations/presentation/controllers/decision_simulation_controller.dart';
import 'package:var_os_app/features/simulations/presentation/screens/decision_result_screen.dart';

import '../simulations/fakes.dart';
import 'fakes.dart';

void main() {
  Future<void> pumpTab(
    WidgetTester tester, {
    required DecisionsRepository repository,
    FakeSimulationsRepository? simulations,
  }) async {
    // A real router rather than a bare `MaterialApp`: each tile pushes the
    // decision's result screen, so navigation is part of what's under test.
    final router = GoRouter(
      initialLocation: AppRoutes.home,
      routes: [
        GoRoute(
          path: AppRoutes.home,
          builder: (context, state) =>
              const Scaffold(body: MyDecisionsTabContent()),
        ),
        GoRoute(
          path: AppRoutes.decisionResult,
          builder: (context, state) {
            final decision = state.extra! as DecisionRef;
            return DecisionResultScreen(
              decisionId: decision.id,
              title: decision.title,
            );
          },
        ),
      ],
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          decisionsRepositoryProvider.overrideWithValue(repository),
          simulationsRepositoryProvider.overrideWithValue(
            simulations ?? FakeSimulationsRepository(),
          ),
        ],
        child: MaterialApp.router(routerConfig: router),
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

  testWidgets('tapping a decision opens its result screen', (tester) async {
    await pumpTab(
      tester,
      repository: FakeDecisionsRepository(
        decisions: [
          testDecision(id: 'd1', title: 'Oferta de trabajo Z', status: 'draft'),
        ],
      ),
    );

    await tester.tap(find.text('Oferta de trabajo Z'));
    await tester.pumpAndSettle();

    expect(find.byType(DecisionResultScreen), findsOneWidget);
  });

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

  testWidgets('marks a completed decision left open for more than 60 days', (
    tester,
  ) async {
    // docs/UX_DESIGN.md Pantalla 10 — and the marker carries words, not just
    // the amber dot (§1.5: color is never the only differentiator).
    await pumpTab(
      tester,
      repository: FakeDecisionsRepository(
        decisions: [
          testDecision(
            id: 'd1',
            title: 'Vieja sin cerrar',
            status: 'completed',
            updatedAt: DateTime.now().subtract(const Duration(days: 90)),
          ),
        ],
      ),
    );

    expect(find.text('Sin cerrar'), findsOneWidget);
  });

  testWidgets('does not mark one whose loop is already closed', (tester) async {
    await pumpTab(
      tester,
      repository: FakeDecisionsRepository(
        decisions: [
          testDecision(
            id: 'd1',
            title: 'Vieja pero cerrada',
            status: 'completed',
            updatedAt: DateTime.now().subtract(const Duration(days: 90)),
          ),
        ],
      ),
      simulations: FakeSimulationsRepository(
        closedLoops: [testOutcome(decisionId: 'd1')],
      ),
    );

    expect(find.text('Sin cerrar'), findsNothing);
  });

  testWidgets('does not nag before the 60 days are up', (tester) async {
    // "invita, no presiona": a decision completed last week is not overdue.
    await pumpTab(
      tester,
      repository: FakeDecisionsRepository(
        decisions: [
          testDecision(
            id: 'd1',
            title: 'Recién completada',
            status: 'completed',
            updatedAt: DateTime.now().subtract(const Duration(days: 7)),
          ),
        ],
      ),
    );

    expect(find.text('Sin cerrar'), findsNothing);
  });

  testWidgets('never marks a decision that was never completed', (
    tester,
  ) async {
    await pumpTab(
      tester,
      repository: FakeDecisionsRepository(
        decisions: [
          testDecision(
            id: 'd1',
            title: 'Vieja pero activa',
            status: 'clarifying',
            updatedAt: DateTime.now().subtract(const Duration(days: 400)),
          ),
        ],
      ),
    );

    expect(find.text('Sin cerrar'), findsNothing);
  });

  testWidgets('reads the outcomes list once, not once per row', (tester) async {
    final simulations = FakeSimulationsRepository();
    await pumpTab(
      tester,
      repository: FakeDecisionsRepository(
        decisions: [
          for (var i = 0; i < 5; i++)
            testDecision(
              id: 'd$i',
              title: 'Decisión $i',
              status: 'completed',
              updatedAt: DateTime.now().subtract(const Duration(days: 90)),
            ),
        ],
      ),
      simulations: simulations,
    );

    expect(find.text('Sin cerrar'), findsNWidgets(5));
    expect(simulations.outcomesReads, 1);
  });
}
