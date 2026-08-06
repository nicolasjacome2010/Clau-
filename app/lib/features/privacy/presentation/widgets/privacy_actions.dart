import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../design_system/var_palette.dart';
import '../../../../design_system/var_spacing.dart';
import '../../../../design_system/var_typography.dart';
import '../controllers/privacy_controller.dart';

/// The two GDPR actions, shared by Memoria (Pantalla 12) and Ajustes
/// (Pantalla 15).
///
/// One widget rather than two copies because they are the same two rights:
/// the spec puts them in Memoria so they're visible rather than buried in
/// a submenu, and in Ajustes because that is where people look for them.
class PrivacyActions extends ConsumerWidget {
  const PrivacyActions({super.key});

  Future<void> _confirmErase(BuildContext context, WidgetRef ref) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('¿Borrar todo?'),
        // Names what goes, in the user's terms. "Se eliminarán tus datos"
        // is technically true and tells them nothing.
        content: const Text(
          'Se borran tus decisiones, sus simulaciones, lo que el sistema '
          'aprendió sobre vos y tus objetivos. No hay forma de recuperarlo.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('Cancelar'),
          ),
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('Borrar todo'),
          ),
        ],
      ),
    );

    if (confirmed ?? false) {
      await ref.read(privacyControllerProvider.notifier).eraseMyData();
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(privacyControllerProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Wrap, not Row: two Spanish labels of this length don't fit side
        // by side on a narrow phone, and a second line beats a clipped
        // button.
        Wrap(
          spacing: VarSpacing.sm,
          runSpacing: VarSpacing.xs,
          children: [
            OutlinedButton(
              onPressed: state.isBusy
                  ? null
                  : () => ref
                        .read(privacyControllerProvider.notifier)
                        .exportMyData(),
              child: const Text('Exportar mis datos'),
            ),
            TextButton(
              onPressed: state.isBusy
                  ? null
                  : () => _confirmErase(context, ref),
              style: TextButton.styleFrom(
                foregroundColor: context.varColors.signalLow,
              ),
              child: const Text('Borrar todo mi historial'),
            ),
          ],
        ),
        if (state.isBusy) ...[
          const SizedBox(height: VarSpacing.sm),
          Row(
            children: [
              const SizedBox(
                width: 16,
                height: 16,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
              const SizedBox(width: VarSpacing.sm),
              Text(
                state.inFlight == 'export'
                    ? 'Preparando tu copia…'
                    : 'Borrando…',
                style: VarTypography.body(12, context.varColors.textSecondary),
              ),
            ],
          ),
        ],
        if (state.message != null) ...[
          const SizedBox(height: VarSpacing.sm),
          Text(
            state.message!,
            style: VarTypography.body(
              12,
              state.isError
                  ? context.varColors.signalLow
                  : context.varColors.textSecondary,
            ),
          ),
        ],
      ],
    );
  }
}
