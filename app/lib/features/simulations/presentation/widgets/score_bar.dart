import 'package:flutter/material.dart';

import '../../../../design_system/var_colors.dart';
import '../../../../design_system/var_motion.dart';
import '../../../../design_system/var_spacing.dart';
import '../../../../design_system/var_typography.dart';

/// Which end of a 0-100 score is the good one. Alignment/reversibility read
/// "higher is better"; risk reads the other way — so the same 72 is a green
/// bar on one row and a red one on the next, and hardcoding "high = green"
/// would have quietly mislabelled every risk score.
enum ScorePolarity { higherIsBetter, lowerIsBetter }

/// A labelled 0-100 score bar (docs/UX_DESIGN.md Pantalla 7).
///
/// Two spec rules are load-bearing here:
/// - §1.5: never color alone — every bar carries its numeric value and a
///   text label, and the fill length itself encodes the score, so the
///   information survives color blindness entirely.
/// - §3: "se rellena de izquierda a derecha en 400ms al aparecer (nunca
///   aparece ya llena — refuerza que es un cálculo, no un dato estático)".
class ScoreBar extends StatefulWidget {
  const ScoreBar({
    super.key,
    required this.label,
    required this.score,
    this.polarity = ScorePolarity.higherIsBetter,
  });

  final String label;
  final double score;
  final ScorePolarity polarity;

  @override
  State<ScoreBar> createState() => _ScoreBarState();
}

class _ScoreBarState extends State<ScoreBar> {
  /// docs/UX_DESIGN.md §3 asks for 400ms — longer than `VarMotion`'s
  /// micro-interaction band but well inside its non-streaming ceiling.
  static const _fillDuration = Duration(milliseconds: 400);

  double _shownFraction = 0;

  @override
  void initState() {
    super.initState();
    // Next frame, so the bar is mounted empty and then animates — starting
    // at the final value would skip the fill the spec asks for.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) setState(() => _shownFraction = _targetFraction);
    });
  }

  @override
  void didUpdateWidget(ScoreBar oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.score != widget.score) {
      setState(() => _shownFraction = _targetFraction);
    }
  }

  double get _targetFraction => (widget.score.clamp(0, 100)) / 100;

  Color get _color {
    final good = widget.polarity == ScorePolarity.higherIsBetter
        ? widget.score
        : 100 - widget.score;
    if (good >= 66) return VarColors.signalHighDark;
    if (good >= 33) return VarColors.signalMediumDark;
    return VarColors.signalLowDark;
  }

  @override
  Widget build(BuildContext context) {
    final rounded = widget.score.round();

    return Semantics(
      label: '${widget.label}: $rounded de 100',
      child: Padding(
        padding: const EdgeInsets.only(bottom: VarSpacing.sm),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  widget.label,
                  style: VarTypography.body(12, VarColors.textSecondaryDark),
                ),
                Text(
                  '$rounded%',
                  style: VarTypography.mono(12, VarColors.textPrimaryDark),
                ),
              ],
            ),
            const SizedBox(height: VarSpacing.xs),
            ClipRRect(
              borderRadius: BorderRadius.circular(3),
              child: Stack(
                children: [
                  Container(height: 6, color: VarColors.dividerDark),
                  AnimatedFractionallySizedBox(
                    duration: _fillDuration,
                    curve: VarMotion.enter,
                    widthFactor: _shownFraction,
                    alignment: Alignment.centerLeft,
                    child: Container(height: 6, color: _color),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
