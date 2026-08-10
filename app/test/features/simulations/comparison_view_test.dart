import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:var_os_app/core/routing/app_routes.dart';
import 'package:var_os_app/features/decisions/domain/decision_ref.dart';
import 'package:var_os_app/features/decisions/presentation/controllers/decisions_controller.dart';
import 'package:var_os_app/features/memory/presentation/controllers/bias_profile_controller.dart';
import 'package:var_os_app/features/simulations/domain/simulation.dart';
import 'package:var_os_app/features/simulations/presentation/controllers/decision_simulation_controller.dart';
import 'package:var_os_app/features/simulations/presentation/screens/decision_result_screen.dart';
import 'package:var_os_app/features/simulations/presentation/widgets/comparison_view.dart';
import 'package:var_os_app/features/simulations/presentation/widgets/scenario_card.dart';

import '../decisions/fakes.dart';
import '../memory/fakes.dart';
import 'fakes.dart';

void main() {
  SimulationScenario scenarioWithGoals({
    required String id,
    required String title,
    required int rank,
    List<GoalAlignment> alignments = const [],
    double riskScore = 30,
    double reversibilityScore = 70,
    double relativeProbability = 40,
  }) {
    return testScenario(
      id: id,
      title: title,
      rank: rank,
      goalAlignmentScores: alignments,
      riskScore: riskScore,
      reversibilityScore: reversibilityScore,
      relativeProbability: relativeProbability,
    );
  }

  Future<void> pumpResult(
    WidgetTester tester, {
    required List<SimulationScenario> scenarios,
    Size? surface,
  }) async {
    if (surface != null) {
      tester.view.physicalSize = surface;
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
    }

    final router = GoRouter(
      initialLocation: AppRoutes.decisionResult,
      routes: [
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
      initialExtra: const DecisionRef(id: 'd1', title: '¿Debo aceptar?'),
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          simulationsRepositoryProvider.overrideWithValue(
            FakeSimulationsRepository(
              simulations: [testSimulation(scenarios: scenarios)],
            ),
          ),
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

  Future<void> openComparison(WidgetTester tester) async {
    await tester.tap(find.text('Comparar'));
    await tester.pumpAndSettle();
  }

  final twoScenarios = [
    scenarioWithGoals(
      id: 's1',
      title: 'Aceptar',
      rank: 1,
      riskScore: 40,
      reversibilityScore: 20,
      relativeProbability: 38,
      alignments: const [
        GoalAlignment(
          goal: 'Crecimiento',
          score: 82,
          justification: 'Más responsabilidad',
        ),
      ],
    ),
    scenarioWithGoals(
      id: 's2',
      title: 'Quedarme',
      rank: 2,
      riskScore: 30,
      reversibilityScore: 75,
      relativeProbability: 29,
      alignments: const [
        GoalAlignment(goal: 'Crecimiento', score: 61, justification: 'Menos'),
      ],
    ),
  ];

  testWidgets('offers the comparison view alongside the scenario view', (
    tester,
  ) async {
    await pumpResult(tester, scenarios: twoScenarios);

    expect(find.text('Escenarios'), findsOneWidget);
    expect(find.text('Comparar'), findsOneWidget);
    expect(find.byType(ComparisonView), findsNothing);

    await openComparison(tester);

    expect(find.text('Comparación'), findsOneWidget);
    expect(find.byType(ComparisonView), findsOneWidget);
    // The two views are alternatives, not a stack.
    expect(find.byType(ScenarioCard), findsNothing);

    await tester.tap(find.text('Ver escenarios'));
    await tester.pumpAndSettle();

    expect(find.byType(ScenarioCard), findsNWidgets(2));
  });

  testWidgets('does not offer comparison for a single scenario', (
    tester,
  ) async {
    // Nothing to compare it against — the toggle would be an empty promise.
    await pumpResult(
      tester,
      scenarios: [scenarioWithGoals(id: 's1', title: 'Único', rank: 1)],
    );

    expect(find.text('Comparar'), findsNothing);
  });

  testWidgets('renders a real table on desktop widths', (tester) async {
    await pumpResult(
      tester,
      scenarios: twoScenarios,
      surface: const Size(1200, 1400),
    );
    await openComparison(tester);

    expect(find.byType(Table), findsOneWidget);
    expect(find.byType(PageView), findsNothing);
    expect(find.text('Criterio'), findsOneWidget);
    expect(find.text('Aceptar'), findsWidgets);
    expect(find.text('Quedarme'), findsWidgets);
  });

  testWidgets('renders swipeable criteria on mobile widths', (tester) async {
    await pumpResult(
      tester,
      scenarios: twoScenarios,
      surface: const Size(400, 1400),
    );
    await openComparison(tester);

    expect(find.byType(PageView), findsOneWidget);
    expect(find.byType(Table), findsNothing);
    // The first criterion group, plus a legible statement of where the user
    // is — the dots alone would say nothing to a screen reader.
    expect(find.textContaining('1 de 4'), findsOneWidget);
  });

  testWidgets('swiping moves between criteria on mobile', (tester) async {
    await pumpResult(
      tester,
      scenarios: twoScenarios,
      surface: const Size(400, 1400),
    );
    await openComparison(tester);

    await tester.drag(find.byType(PageView), const Offset(-400, 0));
    await tester.pumpAndSettle();

    expect(find.textContaining('2 de 4'), findsOneWidget);
    expect(find.textContaining('Riesgo'), findsWidgets);
  });

  testWidgets('shows every criterion the spec asks for', (tester) async {
    await pumpResult(
      tester,
      scenarios: twoScenarios,
      surface: const Size(1200, 1400),
    );
    await openComparison(tester);

    expect(find.text('Crecimiento'), findsOneWidget);
    expect(find.text('Riesgo'), findsOneWidget);
    expect(find.text('Reversibilidad'), findsOneWidget);
    expect(find.text('Probabilidad relativa'), findsOneWidget);
    // Values are text as well as bar length (docs/UX_DESIGN.md §1.5).
    expect(find.text('82%'), findsOneWidget);
    expect(find.text('61%'), findsOneWidget);
    expect(find.text('38%'), findsOneWidget);
  });

  testWidgets('a goal one scenario was never scored against reads as absent', (
    tester,
  ) async {
    // Not as a zero: "sin dato" and "scores terribly" are different claims.
    await pumpResult(
      tester,
      surface: const Size(1200, 1400),
      scenarios: [
        scenarioWithGoals(
          id: 's1',
          title: 'Aceptar',
          rank: 1,
          alignments: const [
            GoalAlignment(goal: 'Crecimiento', score: 82, justification: ''),
          ],
        ),
        scenarioWithGoals(
          id: 's2',
          title: 'Quedarme',
          rank: 2,
          alignments: const [
            GoalAlignment(goal: 'Estabilidad', score: 70, justification: ''),
          ],
        ),
      ],
    );
    await openComparison(tester);

    expect(find.text('Crecimiento'), findsOneWidget);
    expect(find.text('Estabilidad'), findsOneWidget);
    expect(find.text('—'), findsNWidgets(2));
    expect(find.text('0%'), findsNothing);
  });
}
