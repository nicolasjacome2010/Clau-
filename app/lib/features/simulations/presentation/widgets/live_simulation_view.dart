import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../../../design_system/var_palette.dart';
import '../../../../design_system/var_spacing.dart';
import '../../../../design_system/var_typography.dart';
import '../../domain/simulation_progress.dart';

/// Pantalla 6 — Simulación en vivo (docs/UX_DESIGN.md).
///
/// Lights up each of the six rows as `DecisionSimulationController.run()`
/// folds real `SimulationStageProgress` events from `POST .../simulations/
/// stream` into `progress`. Never a synthetic progress bar: a row is either
/// not started, in progress, or done, and it says so with a distinct shape
/// per state (never color alone — docs/UX_DESIGN.md §1.5), not a percentage
/// this client can't actually observe per stage.
class LiveSimulationView extends StatefulWidget {
  const LiveSimulationView({super.key, required this.progress});

  final LiveSimulationProgress progress;

  /// docs/UX_DESIGN.md Pantalla 6: "si excede ~15s en una etapa ... aparece
  /// micro-copy tranquilizador". Restarted every time the visible progress
  /// changes, so it reflects a stall on the *current* stage, not the run as
  /// a whole.
  static const reassuranceAfter = Duration(seconds: 15);

  @override
  State<LiveSimulationView> createState() => _LiveSimulationViewState();
}

class _LiveSimulationViewState extends State<LiveSimulationView> {
  Timer? _timer;
  bool _showReassurance = false;
  late String _lastSignature;

  @override
  void initState() {
    super.initState();
    _lastSignature = _signatureOf(widget.progress);
    _timer = Timer(LiveSimulationView.reassuranceAfter, _onReassuranceDue);
  }

  @override
  void didUpdateWidget(covariant LiveSimulationView oldWidget) {
    super.didUpdateWidget(oldWidget);
    final signature = _signatureOf(widget.progress);
    if (signature == _lastSignature) return;
    _lastSignature = signature;
    _timer?.cancel();
    setState(() => _showReassurance = false);
    _timer = Timer(LiveSimulationView.reassuranceAfter, _onReassuranceDue);
  }

  void _onReassuranceDue() {
    if (mounted) setState(() => _showReassurance = true);
  }

  String _signatureOf(LiveSimulationProgress progress) {
    return SimulationStageGroup.values
        .map((group) => progress.statusFor(group))
        .join();
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final statuses = {
      for (final group in SimulationStageGroup.values)
        group: widget.progress.statusFor(group),
    };
    final doneCount = statuses.values
        .where((status) => status == StageStatus.done)
        .length;

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(VarSpacing.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            for (final entry in statuses.entries)
              _StageRow(group: entry.key, status: entry.value),
            const SizedBox(height: VarSpacing.lg),
            _BranchingLines(
              fraction: doneCount / SimulationStageGroup.values.length,
            ),
            if (_showReassurance) ...[
              const SizedBox(height: VarSpacing.md),
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

class _StageRow extends StatelessWidget {
  const _StageRow({required this.group, required this.status});

  final SimulationStageGroup group;
  final StageStatus status;

  @override
  Widget build(BuildContext context) {
    final color = status == StageStatus.notStarted
        ? context.varColors.textSecondary
        : context.varColors.accentPrimary;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: VarSpacing.xs),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _StatusGlyph(status: status, color: color),
          const SizedBox(width: VarSpacing.sm),
          Text(group.label, style: VarTypography.body(16, color)),
        ],
      ),
    );
  }
}

/// Three visibly different shapes — filled check, a small spinner, an
/// outlined circle — so the state reads without relying on `color` at all.
class _StatusGlyph extends StatelessWidget {
  const _StatusGlyph({required this.status, required this.color});

  final StageStatus status;
  final Color color;

  @override
  Widget build(BuildContext context) {
    const size = 18.0;
    return switch (status) {
      StageStatus.done => Icon(Icons.check_circle, size: size, color: color),
      StageStatus.inProgress => SizedBox(
        width: size,
        height: size,
        child: CircularProgressIndicator(strokeWidth: 2, color: color),
      ),
      StageStatus.notStarted => Icon(
        Icons.circle_outlined,
        size: size,
        color: color,
      ),
    };
  }
}

/// The wireframe's "líneas ramificándose progresivamente": a trunk that
/// grows a branch per completed row. Continuous motion here communicates
/// real work in progress, the one documented exception to `VarMotion`'s
/// duration ceiling (see its class doc) — everywhere else in this app,
/// motion this long would be decoration, not signal.
class _BranchingLines extends StatefulWidget {
  const _BranchingLines({required this.fraction});

  /// 0..1 — how many of the six rows are done.
  final double fraction;

  @override
  State<_BranchingLines> createState() => _BranchingLinesState();
}

class _BranchingLinesState extends State<_BranchingLines>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 3),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final color = context.varColors.accentPrimary;
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, _) => CustomPaint(
        size: const Size(double.infinity, 72),
        painter: _BranchingLinesPainter(
          fraction: widget.fraction,
          pulse: _controller.value,
          color: color,
          faintColor: context.varColors.divider,
        ),
      ),
    );
  }
}

class _BranchingLinesPainter extends CustomPainter {
  _BranchingLinesPainter({
    required this.fraction,
    required this.pulse,
    required this.color,
    required this.faintColor,
  });

  final double fraction;
  final double pulse;
  final Color color;
  final Color faintColor;

  static final _branchCount = SimulationStageGroup.values.length;

  @override
  void paint(Canvas canvas, Size size) {
    final trunkPaint = Paint()
      ..color = faintColor
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke;
    final origin = Offset(0, size.height / 2);
    final trunkEnd = Offset(size.width * 0.15, size.height / 2);
    canvas.drawLine(origin, trunkEnd, trunkPaint);

    final branchesDone = (fraction * _branchCount).round();
    for (var i = 0; i < _branchCount; i++) {
      final start = Offset(
        size.width * (0.15 + 0.7 * i / _branchCount),
        size.height / 2,
      );
      final spread = (i.isEven ? -1 : 1) * (0.18 + 0.06 * i);
      final end = Offset(
        size.width * (0.15 + 0.7 * (i + 1) / _branchCount),
        size.height / 2 + size.height * spread,
      );

      final isDone = i < branchesDone;
      final isActive = i == branchesDone;
      final paint = Paint()
        ..strokeWidth = 2
        ..style = PaintingStyle.stroke
        ..color = isDone
            ? color
            : isActive
            ? color.withValues(alpha: 0.35 + 0.35 * _pulseWave())
            : faintColor;

      canvas.drawLine(start, end, paint);
    }
  }

  double _pulseWave() => 0.5 + 0.5 * math.sin(pulse * 2 * math.pi);

  @override
  bool shouldRepaint(covariant _BranchingLinesPainter oldDelegate) {
    return oldDelegate.fraction != fraction ||
        oldDelegate.pulse != pulse ||
        oldDelegate.color != color;
  }
}
