import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:var_os_app/features/auth/presentation/controllers/session_controller.dart';
import 'package:var_os_app/features/privacy/domain/privacy_repository.dart';
import 'package:var_os_app/features/privacy/presentation/controllers/privacy_controller.dart';
import 'package:var_os_app/features/privacy/presentation/widgets/privacy_actions.dart';

import 'fakes.dart';

void main() {
  Future<void> pumpActions(
    WidgetTester tester, {
    required FakePrivacyRepository repository,
    FakeExportSharer? sharer,
    RecordingAuthRepository? auth,
  }) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          privacyRepositoryProvider.overrideWithValue(repository),
          exportSharerProvider.overrideWithValue(sharer ?? FakeExportSharer()),
          authRepositoryProvider.overrideWithValue(
            auth ?? RecordingAuthRepository(),
          ),
        ],
        child: const MaterialApp(
          home: Scaffold(body: SingleChildScrollView(child: PrivacyActions())),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  Future<void> confirmErase(WidgetTester tester) async {
    await tester.tap(find.text('Borrar todo mi historial'));
    await tester.pumpAndSettle();
    // The dialog's own button, not the one that opened it.
    await tester.tap(find.widgetWithText(TextButton, 'Borrar todo'));
    await tester.pumpAndSettle();
  }

  testWidgets('exporting hands the document to the system share sheet', (
    tester,
  ) async {
    final repository = FakePrivacyRepository(export: '{"user": {"id": "u1"}}');
    final sharer = FakeExportSharer();
    await pumpActions(tester, repository: repository, sharer: sharer);

    await tester.tap(find.text('Exportar mis datos'));
    await tester.pumpAndSettle();

    expect(repository.exportCalls, 1);
    expect(sharer.shared.single.content, '{"user": {"id": "u1"}}');
    // A `.json` file, so what the user keeps is portable in the sense the
    // right actually means.
    expect(sharer.shared.single.filename, endsWith('.json'));
  });

  testWidgets('a device with nowhere to share says so', (tester) async {
    await pumpActions(
      tester,
      repository: FakePrivacyRepository(),
      sharer: FakeExportSharer(succeeds: false),
    );

    await tester.tap(find.text('Exportar mis datos'));
    await tester.pumpAndSettle();

    expect(find.textContaining('no ofreció dónde guardarla'), findsOneWidget);
  });

  testWidgets('nothing to export is stated as such, not as a failure', (
    tester,
  ) async {
    await pumpActions(
      tester,
      repository: FakePrivacyRepository(
        exportError: NothingToExportError('none'),
      ),
    );

    await tester.tap(find.text('Exportar mis datos'));
    await tester.pumpAndSettle();

    expect(
      find.textContaining('Todavía no hay nada que exportar'),
      findsOneWidget,
    );
  });

  testWidgets('erasing asks first, and says what goes', (tester) async {
    final repository = FakePrivacyRepository();
    await pumpActions(tester, repository: repository);

    await tester.tap(find.text('Borrar todo mi historial'));
    await tester.pumpAndSettle();

    expect(find.text('¿Borrar todo?'), findsOneWidget);
    // Named in the user's terms, not as "tus datos".
    expect(find.textContaining('tus decisiones'), findsOneWidget);
    expect(find.textContaining('No hay forma de recuperarlo'), findsOneWidget);
    expect(repository.eraseCalls, 0);
  });

  testWidgets('cancelling the dialog erases nothing', (tester) async {
    final repository = FakePrivacyRepository();
    await pumpActions(tester, repository: repository);

    await tester.tap(find.text('Borrar todo mi historial'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Cancelar'));
    await tester.pumpAndSettle();

    expect(repository.eraseCalls, 0);
  });

  testWidgets('confirming erases and ends the session', (tester) async {
    // The sign-out isn't politeness: the token stays valid for a user whose
    // rows are gone, so every screen would fail inexplicably.
    final repository = FakePrivacyRepository();
    final auth = RecordingAuthRepository();
    await pumpActions(tester, repository: repository, auth: auth);

    await confirmErase(tester);

    expect(repository.eraseCalls, 1);
    expect(auth.signOuts, 1);
    expect(find.textContaining('Borramos todo'), findsOneWidget);
  });

  testWidgets('a live subscription blocks erasure with the reason', (
    tester,
  ) async {
    final auth = RecordingAuthRepository();
    await pumpActions(
      tester,
      repository: FakePrivacyRepository(
        eraseError: ActiveSubscriptionError('active'),
      ),
      auth: auth,
    );

    await confirmErase(tester);

    expect(find.textContaining('Cancelá tu suscripción'), findsOneWidget);
    // Still signed in: nothing was deleted.
    expect(auth.signOuts, 0);
  });

  testWidgets('a failed erasure is reported, not swallowed', (tester) async {
    await pumpActions(
      tester,
      repository: FakePrivacyRepository(
        eraseError: PrivacyRepositoryError('boom'),
      ),
    );

    await confirmErase(tester);

    expect(find.text('No pudimos borrar tus datos.'), findsOneWidget);
  });
}
