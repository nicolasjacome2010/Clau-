import 'package:flutter/material.dart';

import '../../../../design_system/var_colors.dart';
import '../../../../design_system/var_motion.dart';
import '../../../../design_system/var_spacing.dart';
import '../../../../design_system/var_typography.dart';

/// A selectable goal chip with the "escala 1.0→1.05→1.0 (150ms)"
/// micro-interaction (docs/UX_DESIGN.md §3).
class GoalChip extends StatefulWidget {
  const GoalChip({
    super.key,
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  State<GoalChip> createState() => _GoalChipState();
}

class _GoalChipState extends State<GoalChip> {
  double _scale = 1.0;

  Future<void> _handleTap() async {
    setState(() => _scale = 1.05);
    await Future<void>.delayed(VarMotion.microMin);
    if (!mounted) return;
    setState(() => _scale = 1.0);
    widget.onTap();
  }

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      selected: widget.selected,
      label: widget.label,
      child: GestureDetector(
        onTap: _handleTap,
        child: AnimatedScale(
          scale: _scale,
          duration: VarMotion.microMin,
          curve: VarMotion.enter,
          child: AnimatedContainer(
            duration: VarMotion.microMax,
            curve: VarMotion.enter,
            constraints: const BoxConstraints(
              minHeight: VarSpacing.minTouchTarget,
            ),
            padding: const EdgeInsets.symmetric(
              horizontal: VarSpacing.md,
              vertical: VarSpacing.sm,
            ),
            decoration: BoxDecoration(
              color: widget.selected
                  ? VarColors.accentPrimary
                  : VarColors.bgSurfaceDark,
              borderRadius: BorderRadius.circular(
                VarSpacing.minTouchTarget / 2,
              ),
              border: Border.all(
                color: widget.selected
                    ? VarColors.accentPrimary
                    : VarColors.dividerDark,
              ),
            ),
            alignment: Alignment.center,
            child: Text(
              widget.label,
              style: VarTypography.body(
                14,
                widget.selected
                    ? VarColors.bgPrimaryDark
                    : VarColors.textPrimaryDark,
                weight: widget.selected ? FontWeight.w600 : FontWeight.w400,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
