import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:var_os_app/core/routing/app_routes.dart';
import 'package:var_os_app/features/decisions/domain/decision_ref.dart';
import 'package:var_os_app/features/decisions/presentation/controllers/decisions_controller.dart';
import 'package:var_os_app/features/memory/presentation/controllers/bias_profile_controller.dart';
import 'package:var_os_app/features/simulations/domain/simulations_repository.dart';
import 'package:var_os_app/features/simulations/presentation/controllers/decision_simulation_controller.dart';
import 'package:var_os_app/features/simulations/presentation/screens/decision_result_screen.dart';
import 'package:var_os_app/features/simulations/presentation/widgets/calibration_needle.dart';
import 'package:var_os_app/features/simulations/presentation/widgets/outcome_section.dart';

import '../decisions/fakes.dart';
import '../memory/fakes.dart';
import 'fakes.dart';

void main() {
  /// Pantalla 11 lives at the bottom of the result screen, so it is pumped
  /// through that screen rather than in isolation — the same "exercise the
  /// real thing" rule the other screen tests follow.
  Future<void> pumpResult(
    WidgetTester tester, {
    required FakeSimulationsRepository repository,
  }) async {
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
          simulationsRepositoryProvider.overrideWithValue(repository),
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

  FakeSimulationsRepository repositoryWithCompletedSimulation({
    SimulationsRepositoryError? outcomeError,
    Completer<void>? outcomeGate,
    String? closestScenarioId,
    double calibrationDelta = 0,
    List<String> systemErrors = const [],
    bool reported = true,
  }) {
    return FakeSimulationsRepository(
      simulations: [
        testSimulation(
          scenarios: [
            testScenario(id: 's1', title: 'Aceptar la oferta', rank: 1),
            testScenario(id: 's2', title: 'Quedarme', rank: 2),
          ],
        ),
      ],
      outcomeError: outcomeError,
      outcomeGate: outcomeGate,
      reportedOutcome: reported
          ? testOutcome(
              closestScenarioId: closestScenarioId,
              calibrationDelta: calibrationDelta,
              systemErrorsIdentified: systemErrors,
            )
          : null,
    );
  }

  Future<void> submit(WidgetTester tester, String text) async {
    // The prompt sits below the scenarios and the synthesis, so it has to be
    // scrolled to before it can be tapped — same as a real user.
    await tester.ensureVisible(find.byType(TextField));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), text);
    await tester.ensureVisible(find.text('Registrar lo que pasó'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Registrar lo que pasó'));
  }

  testWidgets('offers the close-the-loop prompt on a completed simulation', (
    tester,
  ) async {
    await pumpResult(tester, repository: repositoryWithCompletedSimulation());

    expect(find.byType(OutcomeSection), findsOneWidget);
    expect(find.text('¿Qué pasó realmente?'), findsOneWidget);
    expect(find.text('Registrar lo que pasó'), findsOneWidget);
  });

  testWidgets('does not offer it when the simulation never completed', (
    tester,
  ) async {
    // `POST .../outcome` answers 409 without a completed simulation, so
    // offering the prompt would be inviting a guaranteed failure.
    await pumpResult(
      tester,
      repository: FakeSimulationsRepository(
        simulations: [
          testSimulation(
            status: 'partial',
            scenarios: [testScenario(id: 's1', title: 'Parcial', rank: 1)],
          ),
        ],
      ),
    );

    expect(find.byType(OutcomeSection), findsNothing);
  });

  testWidgets('a safety halt shows no close-the-loop prompt either', (
    tester,
  ) async {
    await pumpResult(
      tester,
      repository: FakeSimulationsRepository(
        simulations: [
          testSimulation(
            safeToProceed: false,
            recommendedAction: 'halt_and_refer',
            scenarios: [testScenario(id: 's1', title: 'Oculto', rank: 1)],
          ),
        ],
      ),
    );

    expect(find.byType(OutcomeSection), findsNothing);
  });

  testWidgets('reporting sends the text and confirms with the calibration', (
    tester,
  ) async {
    final repository = repositoryWithCompletedSimulation(
      closestScenarioId: 's1',
      calibrationDelta: 24,
      systemErrors: const ['Subestimamos el tiempo de adaptación'],
    );
    await pumpResult(tester, repository: repository);

    await submit(tester, 'Acepté y me costó adaptarme.');
    await tester.pumpAndSettle();

    expect(repository.outcomeCalls, hasLength(1));
    expect(repository.outcomeCalls.single.decisionId, 'd1');
    expect(
      repository.outcomeCalls.single.reportedOutcome,
      'Acepté y me costó adaptarme.',
    );

    expect(find.text('El sistema aprendió algo'), findsOneWidget);
    expect(find.byType(CalibrationNeedle), findsOneWidget);
    expect(find.text('24'), findsOneWidget);
    expect(find.text('Lo más parecido fue: Aceptar la oferta'), findsOneWidget);
    expect(find.text('· Subestimamos el tiempo de adaptación'), findsOneWidget);
    // The prompt is gone: the loop is closed for this session.
    expect(find.text('Registrar lo que pasó'), findsNothing);
  });

  testWidgets('a blind spot is stated, not hidden behind a nearest match', (
    tester,
  ) async {
    // docs/REALITY_ENGINE.md §2: `closest_scenario_id: null` is a valuable
    // result, never to be forced into a false match.
    await pumpResult(
      tester,
      repository: repositoryWithCompletedSimulation(closestScenarioId: null),
    );

    await submit(tester, 'Pasó algo que nadie vio venir.');
    await tester.pumpAndSettle();

    expect(
      find.textContaining('no se parece a ninguno de los escenarios'),
      findsOneWidget,
    );
    expect(find.textContaining('Lo más parecido fue'), findsNothing);
  });

  testWidgets('an empty report is not sent', (tester) async {
    final repository = repositoryWithCompletedSimulation();
    await pumpResult(tester, repository: repository);

    await submit(tester, '   ');
    await tester.pumpAndSettle();

    expect(repository.outcomeCalls, isEmpty);
    expect(find.text('Registrar lo que pasó'), findsOneWidget);
  });

  testWidgets('shows the calibrating state while the request is in flight', (
    tester,
  ) async {
    final gate = Completer<void>();
    await pumpResult(
      tester,
      repository: repositoryWithCompletedSimulation(outcomeGate: gate),
    );

    await submit(tester, 'Acepté la oferta.');
    await tester.pump();

    expect(find.text('Calibrando…'), findsOneWidget);
    expect(find.text('Registrar lo que pasó'), findsNothing);

    gate.complete();
    await tester.pumpAndSettle();

    expect(find.text('El sistema aprendió algo'), findsOneWidget);
  });

  testWidgets('a 503 says nothing was saved and the retry is safe', (
    tester,
  ) async {
    await pumpResult(
      tester,
      repository: repositoryWithCompletedSimulation(
        outcomeError: CalibrationUnavailableError('unavailable'),
      ),
    );

    await submit(tester, 'Acepté la oferta.');
    await tester.pumpAndSettle();

    expect(find.textContaining('No se guardó'), findsOneWidget);
    expect(find.text('Registrar lo que pasó'), findsOneWidget);
  });

  testWidgets('a 409 tells the user to simulate first, not "algo salió mal"', (
    tester,
  ) async {
    await pumpResult(
      tester,
      repository: repositoryWithCompletedSimulation(
        outcomeError: NoCompletedSimulationError('no completed simulation'),
      ),
    );

    await submit(tester, 'Acepté la oferta.');
    await tester.pumpAndSettle();

    expect(find.textContaining('Primero necesitás simular'), findsOneWidget);
  });

  testWidgets('any other failure is reported without losing the prompt', (
    tester,
  ) async {
    await pumpResult(
      tester,
      repository: repositoryWithCompletedSimulation(
        outcomeError: SimulationsRepositoryError('boom'),
      ),
    );

    await submit(tester, 'Acepté la oferta.');
    await tester.pumpAndSettle();

    expect(find.text('No pudimos registrar lo que pasó.'), findsOneWidget);
    expect(find.text('Registrar lo que pasó'), findsOneWidget);
  });
}
