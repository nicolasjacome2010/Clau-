import 'package:flutter/material.dart';

import '../../../../design_system/var_colors.dart';
import '../../../../design_system/var_spacing.dart';
import '../../../../design_system/var_typography.dart';

/// Shown instead of any simulation result when Reality Engine's Safety Gate
/// (Agente 0) returns `halt_and_refer`.
///
/// docs/PRD.md §18 is unambiguous: on a detected crisis the product
/// "se niega y redirige" — it must never render scenarios about the
/// situation anyway. This widget is the client half of that refusal, and
/// it is deliberately the only thing on screen in that state: no scenario
/// list underneath, no "ver de todos modos" escape hatch.
///
/// **No specific hotline numbers are hardcoded here, and that is on
/// purpose.** Crisis resources are country- and language-specific, and a
/// wrong or dead number shown to someone in crisis is worse than none.
/// Wiring a real, locale-aware resource list — reviewed by the
/// professionals docs/PRD.md §18 already says this product needs before
/// launch — is a required deliverable, not an optional polish item. Until
/// that exists this copy points to professional help in general terms
/// rather than inventing specifics.
class SafetyReferral extends StatelessWidget {
  const SafetyReferral({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(VarSpacing.lg),
      decoration: BoxDecoration(
        color: VarColors.bgElevatedDark,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: VarColors.signalMediumDark),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Esto merece más que una simulación',
            style: VarTypography.display(20, VarColors.textPrimaryDark),
          ),
          const SizedBox(height: VarSpacing.md),
          Text(
            'Por lo que escribiste, generar escenarios no es lo que necesitas '
            'ahora mismo — y fingir que sí sería irresponsable de nuestra parte.',
            style: VarTypography.body(16, VarColors.textPrimaryDark),
          ),
          const SizedBox(height: VarSpacing.sm),
          Text(
            'Hablar con un profesional de salud mental, o con alguien de '
            'confianza, va a ayudarte más que cualquier cosa que podamos '
            'calcular. Si estás en peligro inmediato, contacta a los servicios '
            'de emergencia de tu país.',
            style: VarTypography.body(16, VarColors.textPrimaryDark),
          ),
          const SizedBox(height: VarSpacing.md),
          Text(
            'Tu decisión quedó guardada. Podés volver cuando quieras.',
            style: VarTypography.body(12, VarColors.textSecondaryDark),
          ),
        ],
      ),
    );
  }
}
