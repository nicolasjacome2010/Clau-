import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:var_os_app/core/routing/app_routes.dart';
import 'package:var_os_app/features/clarification/presentation/screens/clarification_screen.dart';
import 'package:var_os_app/features/decisions/domain/decisions_repository.dart';
import 'package:var_os_app/features/decisions/presentation/controllers/decisions_controller.dart';

import '../decisions/fakes.dart';

void main() {
  const rawInput = '¿Debo aceptar la oferta?';

  /// Pumps Clarificación pushed on top of a stand-in Home, so `context.pop()`
  /// after a successful create has somewhere real to land.
  Future<void> pumpClarification(
    WidgetTester tester, {
    required FakeDecisionsRepository repository,
  }) async {
    final router = GoRouter(
      initialLocation: AppRoutes.home,
      routes: [
        GoRoute(
          path: AppRoutes.home,
          builder: (context, state) => const Scaffold(body: Text('Home')),
        ),
        GoRoute(
          path: AppRoutes.clarification,
          builder: (context, state) =>
              ClarificationScreen(rawInput: state.extra! as String),
        ),
      ],
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [decisionsRepositoryProvider.overrideWithValue(repository)],
        child: MaterialApp.router(routerConfig: router),
      ),
    );
    await tester.pumpAndSettle();

    router.push(AppRoutes.clarification, extra: rawInput);
    await tester.pumpAndSettle();
  }

  Future<void> answerAll(WidgetTester tester) async {
    await tester.tap(find.text('Carrera'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('1-4 semanas'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Dos o más'));
    await tester.pumpAndSettle();
  }

  testWidgets('opens on the vertical question, echoing the captured text', (
    tester,
  ) async {
    await pumpClarification(tester, repository: FakeDecisionsRepository());

    expect(find.text(rawInput), findsOneWidget);
    expect(find.text('¿De qué área es esta decisión?'), findsOneWidget);
    expect(find.text('Carrera'), findsOneWidget);
    expect(find.text('2 preguntas más'), findsOneWidget);
  });

  testWidgets('advances through the questions as they are answered', (
    tester,
  ) async {
    await pumpClarification(tester, repository: FakeDecisionsRepository());

    await tester.tap(find.text('Carrera'));
    await tester.pumpAndSettle();
    expect(find.text('¿Cuál es tu plazo para decidir?'), findsOneWidget);
    expect(find.text('1 pregunta más'), findsOneWidget);

    await tester.tap(find.text('1-4 semanas'));
    await tester.pumpAndSettle();
    expect(
      find.text('¿Ya tienes opciones concretas en mente?'),
      findsOneWidget,
    );
  });

  testWidgets(
    'creates the decision with the chosen vertical and folded context',
    (tester) async {
      final repository = FakeDecisionsRepository();
      await pumpClarification(tester, repository: repository);

      await answerAll(tester);

      expect(repository.createCalls, hasLength(1));
      expect(repository.createCalls.single.vertical, 'career');
      expect(repository.createCalls.single.rawInput, startsWith(rawInput));
      expect(
        repository.createCalls.single.rawInput,
        contains('Plazo para decidir: Entre 1 y 4 semanas'),
      );
    },
  );

  testWidgets('returns to Home once the decision is created', (tester) async {
    await pumpClarification(tester, repository: FakeDecisionsRepository());

    await answerAll(tester);

    expect(find.byType(ClarificationScreen), findsNothing);
    expect(find.text('Home'), findsOneWidget);
  });

  testWidgets('surfaces a retry affordance when creation fails, staying put', (
    tester,
  ) async {
    final repository = FakeDecisionsRepository(
      createError: DecisionsRepositoryError('boom'),
    );
    await pumpClarification(tester, repository: repository);

    await answerAll(tester);

    expect(find.byType(ClarificationScreen), findsOneWidget);
    expect(find.text('No pudimos guardar tu decisión.'), findsOneWidget);

    await tester.tap(find.text('Reintentar'));
    await tester.pumpAndSettle();

    // Retry re-sends the same answers rather than restarting the flow.
    expect(repository.createCalls, hasLength(2));
    expect(repository.createCalls.last.vertical, 'career');
  });
}
