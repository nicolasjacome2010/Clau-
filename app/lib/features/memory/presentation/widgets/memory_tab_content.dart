import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../design_system/var_palette.dart';
import '../../../../design_system/var_spacing.dart';
import '../../../../design_system/var_typography.dart';
import '../../../privacy/presentation/widgets/privacy_actions.dart';
import '../controllers/bias_profile_controller.dart';
import 'bias_pattern_card.dart';
import 'calibration_gauge.dart';

/// Pantalla 12 — Memoria (docs/UX_DESIGN.md): "vista de transparencia
/// radical" over the patterns the system has detected, plus the
/// `calibration_score` gauge and visible GDPR actions.
///
/// "Exportar mis datos" / "Borrar todo mi historial" are real and live
/// here rather than in a settings submenu, which the spec is explicit
/// about: the point is that they're visible. The same two actions also
/// appear in Ajustes, sharing one widget (`PrivacyActions`).
class MemoryTabContent extends ConsumerWidget {
  const MemoryTabContent({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncProfile = ref.watch(biasProfileControllerProvider);

    return asyncProfile.when(
      data: (profile) => ListView(
        padding: const EdgeInsets.all(VarSpacing.lg),
        children: [
          CalibrationGauge(score: profile.calibrationScore),
          const SizedBox(height: VarSpacing.xl),
          Text(
            'Patrones detectados',
            style: VarTypography.display(16, context.varColors.textPrimary),
          ),
          const SizedBox(height: VarSpacing.sm),
          if (profile.biases.isEmpty)
            Text(
              'Aún no hemos detectado patrones — esto aparecerá después de tus primeras simulaciones.',
              style: VarTypography.body(14, context.varColors.textSecondary),
            )
          else
            for (final observation in profile.biases)
              BiasPatternCard(observation: observation),
          const SizedBox(height: VarSpacing.xl),
          const PrivacyActions(),
        ],
      ),
      loading: () =>
          const Center(child: CircularProgressIndicator(strokeWidth: 2)),
      error: (error, _) => Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              'No pudimos cargar tu memoria.',
              style: VarTypography.body(12, context.varColors.signalLow),
            ),
            TextButton(
              onPressed: () =>
                  ref.read(biasProfileControllerProvider.notifier).refresh(),
              child: const Text('Reintentar'),
            ),
          ],
        ),
      ),
    );
  }
}
