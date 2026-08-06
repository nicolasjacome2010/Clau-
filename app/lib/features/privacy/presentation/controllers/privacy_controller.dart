import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_client.dart';
import '../../../auth/presentation/controllers/session_controller.dart';
import '../../data/api_privacy_repository.dart';
import '../../data/share_plus_export_sharer.dart';
import '../../domain/export_sharer.dart';
import '../../domain/privacy_repository.dart';

final privacyRepositoryProvider = Provider<PrivacyRepository>(
  (ref) => ApiPrivacyRepository(ref.read(dioProvider)),
);

final exportSharerProvider = Provider<ExportSharer>(
  (ref) => const SharePlusExportSharer(),
);

/// Which privacy action is in flight, and what to tell the user about the
/// last one. Kept apart from the screens that host the buttons because
/// both Memoria (Pantalla 12) and Ajustes (Pantalla 15) offer them.
class PrivacyActionState {
  const PrivacyActionState({this.inFlight, this.message, this.isError = false});

  /// `'export'` | `'erase'` | `null`.
  final String? inFlight;
  final String? message;
  final bool isError;

  bool get isBusy => inFlight != null;
}

class PrivacyController extends Notifier<PrivacyActionState> {
  @override
  PrivacyActionState build() => const PrivacyActionState();

  Future<void> exportMyData() async {
    if (state.isBusy) return;
    state = const PrivacyActionState(inFlight: 'export');

    try {
      final document = await ref.read(privacyRepositoryProvider).exportMyData();
      final shared = await ref
          .read(exportSharerProvider)
          .share(filename: 'var-os-datos.json', content: document);
      state = PrivacyActionState(
        message: shared
            ? 'Listo: tu copia salió en el formato que elijas guardar.'
            : 'Tu copia está lista, pero este dispositivo no ofreció dónde '
                  'guardarla.',
        isError: !shared,
      );
    } on NothingToExportError {
      state = const PrivacyActionState(
        message: 'Todavía no hay nada que exportar: no guardamos datos tuyos.',
      );
    } catch (error) {
      state = const PrivacyActionState(
        message: 'No pudimos preparar tu exportación.',
        isError: true,
      );
    }
  }

  /// Erases everything and ends the session.
  ///
  /// The sign-out is not politeness: the token stays valid for a user whose
  /// rows are gone, so staying signed in would leave every screen failing
  /// for reasons the UI couldn't explain.
  Future<void> eraseMyData() async {
    if (state.isBusy) return;
    state = const PrivacyActionState(inFlight: 'erase');

    try {
      await ref.read(privacyRepositoryProvider).eraseMyData();
      await ref.read(authRepositoryProvider).signOut();
      state = const PrivacyActionState(
        message: 'Borramos todo. Gracias por habernos dejado acompañarte.',
      );
    } on ActiveSubscriptionError {
      state = const PrivacyActionState(
        message:
            'Cancelá tu suscripción antes de borrar tus datos, así Stripe '
            'deja de cobrarte. Podés hacerlo desde Suscripción.',
        isError: true,
      );
    } catch (error) {
      state = const PrivacyActionState(
        message: 'No pudimos borrar tus datos.',
        isError: true,
      );
    }
  }
}

final privacyControllerProvider =
    NotifierProvider<PrivacyController, PrivacyActionState>(
      PrivacyController.new,
    );
