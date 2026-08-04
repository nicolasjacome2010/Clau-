import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/routing/app_routes.dart';
import '../../../design_system/var_colors.dart';
import '../../../design_system/var_typography.dart';

/// Pantalla 1 — Splash (docs/UX_DESIGN.md §2): the wordmark plus a
/// once-only 600ms animation of a line bifurcating into three and
/// converging back into one point — meant to communicate the product's
/// essence ("simulas futuros posibles, tú decides") in the very first
/// frame, not as generic loading decoration.
class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 600),
    );
    _controller.addStatusListener(_onStatusChanged);
    _controller.forward();
  }

  void _onStatusChanged(AnimationStatus status) {
    if (status == AnimationStatus.completed && mounted) {
      context.go(AppRoutes.onboarding);
    }
  }

  @override
  void dispose() {
    _controller.removeStatusListener(_onStatusChanged);
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: VarColors.bgPrimaryDark,
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            SizedBox(
              width: 120,
              height: 80,
              child: AnimatedBuilder(
                animation: _controller,
                builder: (context, _) => CustomPaint(
                  painter: _BranchingLinePainter(progress: _controller.value),
                ),
              ),
            ),
            const SizedBox(height: 24),
            Text(
              'VAR OS',
              style: VarTypography.display(31, VarColors.textPrimaryDark),
            ),
          ],
        ),
      ),
    );
  }
}

/// One line splitting into three, then converging back into one — driven
/// by a single 0..1 progress value so it stays a pure function of
/// `AnimationController.value` (no imperative animation state).
class _BranchingLinePainter extends CustomPainter {
  _BranchingLinePainter({required this.progress});

  final double progress;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = VarColors.accentPrimary
      ..strokeWidth = 1.5
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    final start = Offset(size.width / 2, 0);
    final end = Offset(size.width / 2, size.height);
    final branchPoints = [
      Offset(size.width * 0.15, size.height * 0.5),
      Offset(size.width * 0.5, size.height * 0.5),
      Offset(size.width * 0.85, size.height * 0.5),
    ];

    // First half: start -> branch points. Second half: branch points -> end.
    final splitT = (progress * 2).clamp(0.0, 1.0);
    final convergeT = ((progress - 0.5) * 2).clamp(0.0, 1.0);

    for (final branch in branchPoints) {
      final splitEnd = Offset.lerp(start, branch, splitT)!;
      canvas.drawLine(start, splitEnd, paint);
      if (convergeT > 0) {
        final convergeEnd = Offset.lerp(branch, end, convergeT)!;
        canvas.drawLine(branch, convergeEnd, paint);
      }
    }
  }

  @override
  bool shouldRepaint(covariant _BranchingLinePainter oldDelegate) =>
      oldDelegate.progress != progress;
}
