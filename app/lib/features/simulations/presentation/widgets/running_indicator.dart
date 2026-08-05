import 'dart:async';

import 'package:flutter/material.dart';

import '../../../../design_system/var_palette.dart';
import '../../../../design_system/var_spacing.dart';
import '../../../../design_system/var_typography.dart';

/// The honest stand-in for Pantalla 6 (Simulación en vivo).
///
/// The real screen lights up each pipeline stage as it completes, over a
/// WebSocket the backend doesn't expose yet. Rather than fake that with a
/// timed animation pretending to know progress it can't observe, this
/// shows an indeterminate wait — and after ~15s the reassuring micro-copy
/// the spec asks for, which is the one part of that screen's behaviour
/// that doesn't depend on real progress data.
class RunningIndicator extends StatefulWidget {
  const RunningIndicator({super.key});

  /// docs/UX_DESIGN.md Pantalla 6: "si excede ~15s ... aparece micro-copy
  /// tranquilizador".
  static const reassuranceAfter = Duration(seconds: 15);

  @override
  State<RunningIndicator> createState() => _RunningIndicatorState();
}

class _RunningIndicatorState extends State<RunningIndicator> {
  Timer? _timer;
  bool _showReassurance = false;

  @override
  void initState() {
    super.initState();
    _timer = Timer(RunningIndicator.reassuranceAfter, () {
      if (mounted) setState(() => _showReassurance = true);
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(VarSpacing.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const CircularProgressIndicator(strokeWidth: 2),
            const SizedBox(height: VarSpacing.lg),
            Text(
              'Simulando tus escenarios…',
              style: VarTypography.body(16, context.varColors.textPrimary),
            ),
            if (_showReassurance) ...[
              const SizedBox(height: VarSpacing.sm),
              Text(
                'Los escenarios complejos toman un poco más — vale la pena.',
                textAlign: TextAlign.center,
                style: VarTypography.body(12, context.varColors.textSecondary),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
