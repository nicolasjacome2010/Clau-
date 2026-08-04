import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../design_system/var_colors.dart';
import '../../../../design_system/var_spacing.dart';
import '../../../../design_system/var_typography.dart';
import '../controllers/bias_profile_controller.dart';
import 'bias_pattern_card.dart';
import 'calibration_gauge.dart';

/// Pantalla 12 — Memoria (docs/UX_DESIGN.md): "vista de transparencia
/// radical" over the patterns the system has detected, plus the
/// `calibration_score` gauge and visible GDPR actions.
///
/// "Exportar mis datos" / "Borrar todo mi historial" are real buttons
/// (the spec is explicit they must not be hidden in a settings submenu),
/// but the backend has no export/delete-all endpoint yet — tapping either
/// shows a "coming soon" notice rather than faking the action, same
/// posture as Home's decision input before decision creation was wired.
class MemoryTabContent extends ConsumerWidget {
  const MemoryTabContent({super.key});

  void _showComingSoon(BuildContext context, String action) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('$action llega en un próximo módulo.')),
    );
  }

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
            style: VarTypography.display(16, VarColors.textPrimaryDark),
          ),
          const SizedBox(height: VarSpacing.sm),
          if (profile.biases.isEmpty)
            Text(
              'Aún no hemos detectado patrones — esto aparecerá después de tus primeras simulaciones.',
              style: VarTypography.body(14, VarColors.textSecondaryDark),
            )
          else
            for (final observation in profile.biases)
              BiasPatternCard(observation: observation),
          const SizedBox(height: VarSpacing.xl),
          OutlinedButton(
            onPressed: () => _showComingSoon(context, 'Exportar mis datos'),
            child: const Text('Exportar mis datos'),
          ),
          const SizedBox(height: VarSpacing.sm),
          OutlinedButton(
            onPressed: () =>
                _showComingSoon(context, 'Borrar todo mi historial'),
            style: OutlinedButton.styleFrom(
              foregroundColor: VarColors.signalLowDark,
            ),
            child: const Text('Borrar todo mi historial'),
          ),
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
              style: VarTypography.body(12, VarColors.signalLowDark),
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
