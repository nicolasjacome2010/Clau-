import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:var_os_app/features/auth/domain/auth_repository.dart';
import 'package:var_os_app/features/auth/presentation/controllers/session_controller.dart';
import 'package:var_os_app/features/goals/presentation/controllers/goals_controller.dart';
import 'package:var_os_app/features/onboarding/presentation/controllers/pending_goals_flusher.dart';

import '../goals/fakes.dart';
import 'fakes.dart';

class _FakeAuthRepository implements AuthRepository {
  _FakeAuthRepository({this.initialToken});

  final String? initialToken;

  @override
  String? get currentAccessToken => initialToken;

  @override
  Stream<String?> get accessTokenChanges => const Stream<String?>.empty();

  @override
  Future<void> signInWithEmail(String email) async {}

  @override
  Future<void> continueAnonymously() async {}

  @override
  Future<void> signOut() async {}
}

ProviderContainer _container({
  String? token,
  required FakePendingGoalsStore store,
  required FakeGoalsRepository goals,
}) {
  final container = ProviderContainer(
    overrides: [
      authRepositoryProvider.overrideWithValue(
        _FakeAuthRepository(initialToken: token),
      ),
      pendingGoalsStoreProvider.overrideWithValue(store),
      goalsRepositoryProvider.overrideWithValue(goals),
    ],
  );
  addTearDown(container.dispose);
  return container;
}

void main() {
  test('nothing is submitted while there is no session', () async {
    // The goals were captured before Pantalla 3 — there is no token to
    // authenticate POST /v1/goals with yet, and calling it anyway would
    // just 401.
    final store = FakePendingGoalsStore(pending: ['Estabilidad financiera']);
    final goals = FakeGoalsRepository();
    final container = _container(token: null, store: store, goals: goals);

    final submitted = await container.read(pendingGoalsFlusherProvider.future);

    expect(submitted, 0);
    expect(goals.createCalls, isEmpty);
    expect(await store.read(), ['Estabilidad financiera']);
  });

  test('a session delivers every queued goal to the backend', () async {
    final store = FakePendingGoalsStore(
      pending: ['Estabilidad financiera', 'Salud/bienestar'],
    );
    final goals = FakeGoalsRepository();
    final container = _container(token: 'tok', store: store, goals: goals);

    final submitted = await container.read(pendingGoalsFlusherProvider.future);

    expect(submitted, 2);
    expect(goals.createCalls.map((c) => c.name), [
      'Estabilidad financiera',
      'Salud/bienestar',
    ]);
  });

  test('the queue is emptied, so a later run submits nothing again', () async {
    // The guard against the user's goals being created twice — once now,
    // once on the next launch.
    final store = FakePendingGoalsStore(pending: ['Relaciones']);
    final goals = FakeGoalsRepository();
    final container = _container(token: 'tok', store: store, goals: goals);

    await container.read(pendingGoalsFlusherProvider.future);
    expect(await store.read(), isEmpty);

    container.invalidate(pendingGoalsFlusherProvider);
    final second = await container.read(pendingGoalsFlusherProvider.future);

    expect(second, 0);
    expect(goals.createCalls, hasLength(1));
  });

  test(
    'a mid-batch failure leaves exactly the undelivered goals queued',
    () async {
      // The reason the remainder is rewritten after each success: a retry
      // must not re-create the ones that already landed.
      final store = FakePendingGoalsStore(
        pending: ['Estabilidad financiera', 'Salud/bienestar', 'Relaciones'],
      );
      final goals = FakeGoalsRepository(failCreateAfter: 1);
      final container = _container(token: 'tok', store: store, goals: goals);

      final submitted = await container.read(
        pendingGoalsFlusherProvider.future,
      );

      expect(submitted, 1);
      expect(goals.createCalls.map((c) => c.name), ['Estabilidad financiera']);
      expect(await store.read(), ['Salud/bienestar', 'Relaciones']);
    },
  );

  test('the queue shrinks one goal at a time, not all at the end', () async {
    final store = FakePendingGoalsStore(pending: ['Uno', 'Dos']);
    final goals = FakeGoalsRepository();
    final container = _container(token: 'tok', store: store, goals: goals);

    await container.read(pendingGoalsFlusherProvider.future);

    expect(store.writes, [
      ['Dos'],
      <String>[],
    ]);
  });

  test('an empty queue never touches the goals endpoint', () async {
    final store = FakePendingGoalsStore();
    final goals = FakeGoalsRepository();
    final container = _container(token: 'tok', store: store, goals: goals);

    expect(await container.read(pendingGoalsFlusherProvider.future), 0);
    expect(goals.createCalls, isEmpty);
    expect(store.writes, isEmpty);
  });
}
