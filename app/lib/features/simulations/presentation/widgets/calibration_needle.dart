import 'package:flutter/material.dart';

import '../../../../design_system/var_palette.dart';
import '../../../../design_system/var_motion.dart';
import '../../../../design_system/var_spacing.dart';
import '../../../../design_system/var_typography.dart';

/// docs/UX_DESIGN.md Pantalla 11: on closing the loop, "una aguja/indicador
/// que se ajusta sutilmente", communicating that the system learned
/// something.
///
/// It animates from 0 (the neutral center) to the reported
/// `calibration_delta` for exactly that reason — the movement *is* the
/// message, so mounting it already in place would say nothing. Same
/// discipline as `ScoreBar`, and inside `VarMotion.nonStreamingCeiling`
/// because the calibration has already happened: nothing is in progress.
///
/// The number is shown raw, on a -100..100 axis, with no "¡bien calibrado!"
/// copy layered on top. docs/REALITY_ENGINE.md never defines what the sign
/// of `calibration_delta` means, and `UserBiasProfile.with_calibration_delta`
/// describes its own formula as "a starting formula, not a validated
/// calibration model" — inventing an interpretation here would be the one
/// dishonest pixel on an otherwise honest screen.
class CalibrationNeedle extends StatefulWidget {
  const CalibrationNeedle({super.key, required this.delta});

  final double delta;

  @override
  State<CalibrationNeedle> createState() => _CalibrationNeedleState();
}

class _CalibrationNeedleState extends State<CalibrationNeedle> {
  double _shown = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) setState(() => _shown = widget.delta.clamp(-100.0, 100.0));
    });
  }

  @override
  void didUpdateWidget(CalibrationNeedle oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.delta != widget.delta) {
      setState(() => _shown = widget.delta.clamp(-100.0, 100.0));
    }
  }

  @override
  Widget build(BuildContext context) {
    final clamped = widget.delta.clamp(-100.0, 100.0);

    return Semantics(
      label:
          'Ajuste de calibración: ${clamped.toStringAsFixed(0)} '
          'en una escala de -100 a 100',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Ajuste de calibración',
                style: VarTypography.body(12, context.varColors.textSecondary),
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
              const needleWidth = 3.0;
              const height = 20.0;
              final fraction = (_shown + 100) / 200;
              final left = (constraints.maxWidth - needleWidth) * fraction;

              return SizedBox(
                height: height,
                child: Stack(
                  children: [
                    Positioned(
                      top: (height - 6) / 2,
                      left: 0,
                      right: 0,
                      child: Container(
                        height: 6,
                        decoration: BoxDecoration(
                          color: context.varColors.divider,
                          borderRadius: BorderRadius.circular(3),
                        ),
                      ),
                    ),
                    AnimatedPositioned(
                      duration: VarMotion.screenTransitionMax,
                      curve: VarMotion.enter,
                      left: left,
                      top: 0,
                      child: Container(
                        width: needleWidth,
                        height: height,
                        decoration: BoxDecoration(
                          color: context.varColors.accentPrimary,
                          borderRadius: BorderRadius.circular(2),
                        ),
                      ),
                    ),
                  ],
                ),
              );
            },
          ),
          const SizedBox(height: VarSpacing.xs),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                '-100',
                style: VarTypography.mono(12, context.varColors.textSecondary),
              ),
              Text(
                '0',
                style: VarTypography.mono(12, context.varColors.textSecondary),
              ),
              Text(
                '100',
                style: VarTypography.mono(12, context.varColors.textSecondary),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
