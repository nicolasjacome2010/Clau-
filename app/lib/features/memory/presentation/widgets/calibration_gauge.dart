import 'package:flutter/material.dart';

import '../../../../design_system/var_palette.dart';
import '../../../../design_system/var_spacing.dart';
import '../../../../design_system/var_typography.dart';

/// A simple gauge for `calibration_score` (docs/UX_DESIGN.md Pantalla 12:
/// "el calibration_score visualizado como un medidor simple"). The score
/// ranges -100..100 (backend/src/core_api/memory/api/schemas.py's
/// `RecordCalibrationRequest`); this renders it as a dot on a bar with 0
/// centered, plus the raw number — the exact meaning of the sign isn't
/// specified in docs/REALITY_ENGINE.md's Agente 12 spec, so no invented
/// "you're well calibrated!" copy is layered on top of the number.
class CalibrationGauge extends StatelessWidget {
  const CalibrationGauge({super.key, required this.score});

  final double score;

  @override
  Widget build(BuildContext context) {
    final clamped = score.clamp(-100.0, 100.0);
    final fraction = (clamped + 100) / 200;

    return Semantics(
      label:
          'Puntaje de calibración: ${clamped.toStringAsFixed(0)} de -100 a 100',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Calibración',
                style: VarTypography.display(16, context.varColors.textPrimary),
              ),
              Text(
                clamped.toStringAsFixed(0),
                style: VarTypography.mono(16, context.varColors.accentPrimary),
              ),
            ],
          ),
          const SizedBox(height: VarSpacing.sm),
          LayoutBuilder(
            builder: (context, constraints) {
              const dotSize = 12.0;
              final left = (constraints.maxWidth - dotSize) * fraction;
              return SizedBox(
                height: dotSize,
                child: Stack(
                  clipBehavior: Clip.none,
                  children: [
                    Positioned(
                      top: (dotSize - 8) / 2,
                      left: 0,
                      right: 0,
                      child: Container(
                        height: 8,
                        decoration: BoxDecoration(
                          color: context.varColors.divider,
                          borderRadius: BorderRadius.circular(4),
                        ),
                      ),
                    ),
                    Positioned(
                      left: left,
                      child: Container(
                        width: dotSize,
                        height: dotSize,
                        decoration: BoxDecoration(
                          color: context.varColors.accentPrimary,
                          shape: BoxShape.circle,
                        ),
                      ),
                    ),
                  ],
                ),
              );
            },
          ),
        ],
      ),
    );
  }
}
