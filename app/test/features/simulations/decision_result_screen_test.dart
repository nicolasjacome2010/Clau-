import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:var_os_app/core/routing/app_routes.dart';
import 'package:var_os_app/features/decisions/domain/decision_ref.dart';
import 'package:var_os_app/features/decisions/presentation/controllers/decisions_controller.dart';
import 'package:var_os_app/features/memory/presentation/controllers/bias_profile_controller.dart';
import 'package:var_os_app/features/simulations/domain/simulation.dart';
import 'package:var_os_app/features/simulations/domain/simulations_repository.dart';
import 'package:var_os_app/features/simulations/presentation/controllers/decision_simulation_controller.dart';
import 'package:var_os_app/features/simulations/presentation/screens/decision_result_screen.dart';
import 'package:var_os_app/features/simulations/presentation/widgets/running_indicator.dart';
import 'package:var_os_app/features/simulations/presentation/widgets/safety_referral.dart';
import 'package:var_os_app/features/simulations/presentation/widgets/scenario_card.dart';
import 'package:var_os_app/features/simulations/presentation/widgets/synthesis_section.dart';

import '../decisions/fakes.dart';
import '../memory/fakes.dart';
import 'fakes.dart';

void main() {
  Future<void> pumpResult(
    WidgetTester tester, {
    required SimulationsRepository repository,
    String decisionId = 'd1',
  }) async {
    // A real router, as the other screen tests do — the screen is reached by
    // pushing `decisionResult` with a `DecisionRef`, and that wiring is part
    // of what's under test.
    final router = GoRouter(
      initialLocation: AppRoutes.decisionResult,
      routes: [
        GoRoute(
          path: AppRoutes.decisionResult,
          builder: (context, state) {
            final ref = state.extra! as DecisionRef;
            return DecisionResultScreen(decisionId: ref.id, title: ref.title);
          },
        ),
      ],
      // `initialExtra` is how a route that requires `extra` can be the
      // initial location at all.
      initialExtra: DecisionRef(id: decisionId, title: '¿Debo aceptar?'),
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          simulationsRepositoryProvider.overrideWithValue(repository),
          decisionsRepositoryProvider.overrideWithValue(
            FakeDecisionsRepository(),
          ),
          // Closing the loop recalibrates the bias profile, so the screen
          // reaches into `memory` to refresh it.
          memoryRepositoryProvider.overrideWithValue(FakeMemoryRepository()),
        ],
        child: MaterialApp.router(routerConfig: router),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets('shows the decision title in the app bar', (tester) async {
    await pumpResult(tester, repository: FakeSimulationsRepository());

    expect(find.text('¿Debo aceptar?'), findsOneWidget);
  });

  testWidgets('offers to simulate when the decision has no simulation yet', (
    tester,
  ) async {
    await pumpResult(tester, repository: FakeSimulationsRepository());

    expect(
      find.text('Esta decisión todavía no se ha simulado.'),
      findsOneWidget,
    );
    expect(find.byType(ScenarioCard), findsNothing);
  });

  testWidgets('renders scenarios ordered by rank, plus the synthesis', (
    tester,
  ) async {
    await pumpResult(
      tester,
      repository: FakeSimulationsRepository(
        simulations: [
          testSimulation(
            synthesisText: 'Ambos caminos son viables.',
            reflectiveQuestion: '¿Qué versión de vos querés ser en 5 años?',
            scenarios: [
              testScenario(id: 's2', title: 'Quedarme', rank: 2),
              testScenario(id: 's1', title: 'Aceptar la oferta', rank: 1),
            ],
          ),
        ],
      ),
    );

    expect(find.byType(ScenarioCard), findsNWidgets(2));

    final titles = tester
        .widgetList<Text>(find.byType(Text))
        .map((widget) => widget.data)
        .whereType<String>()
        .toList();
    expect(
      titles.indexOf('Aceptar la oferta'),
      lessThan(titles.indexOf('Quedarme')),
    );

    expect(find.byType(SynthesisSection), findsOneWidget);
    expect(find.text('Ambos caminos son viables.'), findsOneWidget);
    expect(
      find.text('¿Qué versión de vos querés ser en 5 años?'),
      findsOneWidget,
    );
  });

  testWidgets('shows the most recent simulation when there are several', (
    tester,
  ) async {
    await pumpResult(
      tester,
      repository: FakeSimulationsRepository(
        simulations: [
          testSimulation(
            id: 'old',
            startedAt: DateTime.utc(2026, 1, 1),
            scenarios: [testScenario(id: 'a', title: 'Vieja', rank: 1)],
          ),
          testSimulation(
            id: 'new',
            startedAt: DateTime.utc(2026, 6, 1),
            scenarios: [testScenario(id: 'b', title: 'Reciente', rank: 1)],
          ),
        ],
      ),
    );

    expect(find.text('Reciente'), findsOneWidget);
    expect(find.text('Vieja'), findsNothing);
  });

  testWidgets('a safety halt shows the referral and no scenarios at all', (
    tester,
  ) async {
    // The load-bearing test of this screen (docs/PRD.md §18): even when the
    // payload still carries scenarios, a halted run must never render them.
    await pumpResult(
      tester,
      repository: FakeSimulationsRepository(
        simulations: [
          testSimulation(
            safeToProceed: false,
            recommendedAction: 'halt_and_refer',
            synthesisText: 'No debería mostrarse.',
            scenarios: [
              testScenario(id: 's1', title: 'No debería mostrarse', rank: 1),
            ],
          ),
        ],
      ),
    );

    expect(find.byType(SafetyReferral), findsOneWidget);
    expect(find.byType(ScenarioCard), findsNothing);
    expect(find.byType(SynthesisSection), findsNothing);
    expect(find.text('No debería mostrarse'), findsNothing);
    expect(find.text('Simular de nuevo'), findsNothing);
  });

  testWidgets('a halt without an explicit action still refers', (tester) async {
    await pumpResult(
      tester,
      repository: FakeSimulationsRepository(
        simulations: [
          testSimulation(
            safeToProceed: false,
            recommendedAction: 'proceed_with_care',
            scenarios: [testScenario(id: 's1', title: 'Oculto', rank: 1)],
          ),
        ],
      ),
    );

    expect(find.byType(SafetyReferral), findsOneWidget);
    expect(find.byType(ScenarioCard), findsNothing);
  });

  testWidgets('a failed simulation offers a retry instead of empty results', (
    tester,
  ) async {
    await pumpResult(
      tester,
      repository: FakeSimulationsRepository(
        simulations: [testSimulation(status: 'failed')],
      ),
    );

    expect(find.text('La simulación no pudo completarse.'), findsOneWidget);
    expect(find.byType(ScenarioCard), findsNothing);
  });

  testWidgets(
    'running a simulation shows the indeterminate wait, then results',
    (tester) async {
      final gate = Completer<void>();
      final repository = FakeSimulationsRepository(
        runGate: gate,
        ranSimulation: testSimulation(
          scenarios: [
            testScenario(id: 's1', title: 'Aceptar la oferta', rank: 1),
          ],
        ),
      );
      await pumpResult(tester, repository: repository);

      await tester.tap(find.text('Simular ahora'));
      await tester.pump();

      expect(find.byType(RunningIndicator), findsOneWidget);

      gate.complete();
      await tester.pumpAndSettle();

      expect(repository.runCalls, ['d1']);
      expect(find.byType(RunningIndicator), findsNothing);
      expect(find.text('Aceptar la oferta'), findsOneWidget);
    },
  );

  testWidgets('a long wait grows reassuring micro-copy instead of a fake bar', (
    tester,
  ) async {
    // docs/UX_DESIGN.md Pantalla 6: past ~15s the wait explains itself. It
    // still never claims progress it can't observe.
    final gate = Completer<void>();
    await pumpResult(
      tester,
      repository: FakeSimulationsRepository(runGate: gate),
    );

    await tester.tap(find.text('Simular ahora'));
    await tester.pump();

    expect(
      find.text('Los escenarios complejos toman un poco más — vale la pena.'),
      findsNothing,
    );

    await tester.pump(
      RunningIndicator.reassuranceAfter + const Duration(seconds: 1),
    );

    expect(
      find.text('Los escenarios complejos toman un poco más — vale la pena.'),
      findsOneWidget,
    );

    gate.complete();
    await tester.pumpAndSettle();
  });

  testWidgets('a failed run surfaces an error and keeps the retry available', (
    tester,
  ) async {
    await pumpResult(
      tester,
      repository: FakeSimulationsRepository(
        runError: SimulationsRepositoryError('boom'),
      ),
    );

    await tester.tap(find.text('Simular ahora'));
    await tester.pumpAndSettle();

    expect(find.text('No pudimos completar la simulación.'), findsOneWidget);
    expect(find.text('Simular ahora'), findsOneWidget);
  });

  testWidgets('a failed load offers a retry', (tester) async {
    await pumpResult(
      tester,
      repository: FakeSimulationsRepository(
        listError: SimulationsRepositoryError('network down'),
      ),
    );

    expect(find.text('No pudimos cargar esta decisión.'), findsOneWidget);
    expect(find.text('Reintentar'), findsOneWidget);
  });

  testWidgets('expanding a scenario reveals its assumptions', (tester) async {
    await pumpResult(
      tester,
      repository: FakeSimulationsRepository(
        simulations: [
          testSimulation(
            scenarios: [
              testScenario(
                id: 's1',
                title: 'Aceptar la oferta',
                rank: 1,
                assumptions: const ['El equipo se mantiene estable'],
              ),
            ],
          ),
        ],
      ),
    );

    expect(find.text('· El equipo se mantiene estable'), findsNothing);

    await tester.tap(find.byType(ScenarioCard));
    await tester.pumpAndSettle();

    expect(find.text('· El equipo se mantiene estable'), findsOneWidget);
  });

  testWidgets('every scenario shows its scores as text, never color alone', (
    tester,
  ) async {
    await pumpResult(
      tester,
      repository: FakeSimulationsRepository(
        simulations: [
          testSimulation(
            scenarios: [
              testScenario(
                id: 's1',
                title: 'Aceptar la oferta',
                rank: 1,
                riskScore: 30,
                reversibilityScore: 70,
                goalAlignmentScores: const [
                  GoalAlignment(
                    goal: 'Estabilidad financiera',
                    score: 80,
                    justification: 'Sueldo mayor',
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
    );

    expect(find.text('Riesgo'), findsOneWidget);
    expect(find.text('30%'), findsOneWidget);
    expect(find.text('Reversibilidad'), findsOneWidget);
    expect(find.text('70%'), findsOneWidget);
    expect(find.text('Alineación · Estabilidad financiera'), findsOneWidget);
    expect(find.text('80%'), findsOneWidget);
  });
}
