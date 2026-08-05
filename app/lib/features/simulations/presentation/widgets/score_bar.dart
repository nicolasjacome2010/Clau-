import 'package:flutter/material.dart';

import '../../../../design_system/var_palette.dart';
import '../../../../design_system/var_motion.dart';
import '../../../../design_system/var_spacing.dart';
import '../../../../design_system/var_typography.dart';

/// Which end of a 0-100 score is the good one. Alignment/reversibility read
/// "higher is better"; risk reads the other way — so the same 72 is a green
/// bar on one row and a red one on the next, and hardcoding "high = green"
/// would have quietly mislabelled every risk score.
///
/// `neutral` is for magnitudes that are neither: a scenario's relative
/// probability is not good news or bad news, and coloring it green or red
/// would state an opinion the system doesn't hold.
enum ScorePolarity { higherIsBetter, lowerIsBetter, neutral }

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
    switch (widget.polarity) {
      case ScorePolarity.neutral:
        return context.varColors.accentPrimary;
      case ScorePolarity.higherIsBetter:
      case ScorePolarity.lowerIsBetter:
        final good = widget.polarity == ScorePolarity.higherIsBetter
            ? widget.score
            : 100 - widget.score;
        if (good >= 66) return context.varColors.signalHigh;
        if (good >= 33) return context.varColors.signalMedium;
        return context.varColors.signalLow;
    }
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
                // The label can be a user-written scenario title, so it
                // takes the slack and truncates; the number never does —
                // it's the part that must stay readable.
                Expanded(
                  child: Text(
                    widget.label,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: VarTypography.body(
                      12,
                      context.varColors.textSecondary,
                    ),
                  ),
                ),
                const SizedBox(width: VarSpacing.sm),
                Text(
                  '$rounded%',
                  style: VarTypography.mono(12, context.varColors.textPrimary),
                ),
              ],
            ),
            const SizedBox(height: VarSpacing.xs),
            ClipRRect(
              borderRadius: BorderRadius.circular(3),
              child: Stack(
                children: [
                  Container(height: 6, color: context.varColors.divider),
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
