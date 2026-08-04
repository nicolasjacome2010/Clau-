import 'dart:async';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/routing/app_routes.dart';
import '../../../../design_system/var_colors.dart';
import '../../../../design_system/var_spacing.dart';
import '../../../../design_system/var_typography.dart';

/// The dominant Home element (docs/UX_DESIGN.md Pantalla 4: "60% del
/// viewport en mobile"): a decision-capture field with a rotating
/// placeholder of anonymized real examples, and a mic affordance.
///
/// Submitting hands off to Pantalla 5 (Clarificación) rather than creating
/// the decision here: `POST /v1/decisions` needs a `vertical` this single
/// free-text field can't supply, and asking is exactly what that screen is
/// for. Voice capture still shows a "coming soon" notice — it needs
/// platform mic permissions + STT wiring this increment doesn't build, a
/// documented gap rather than a feature nobody noticed.
class DecisionInputField extends StatefulWidget {
  const DecisionInputField({super.key});

  @override
  State<DecisionInputField> createState() => _DecisionInputFieldState();
}

class _DecisionInputFieldState extends State<DecisionInputField> {
  static const _examples = [
    '¿Debo aceptar esta oferta de trabajo?',
    '¿Me conviene mudarme a otra ciudad este año?',
    '¿Termino esta relación o la trabajo?',
  ];

  final _controller = TextEditingController();
  Timer? _rotationTimer;
  int _exampleIndex = 0;

  @override
  void initState() {
    super.initState();
    _rotationTimer = Timer.periodic(const Duration(seconds: 4), (_) {
      if (!mounted) return;
      setState(() => _exampleIndex = (_exampleIndex + 1) % _examples.length);
    });
  }

  @override
  void dispose() {
    _rotationTimer?.cancel();
    _controller.dispose();
    super.dispose();
  }

  void _showComingSoon(String feature) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('$feature llega en un próximo módulo.')),
    );
  }

  void _startClarification() {
    final text = _controller.text.trim();
    if (text.isEmpty) return;
    _controller.clear();
    context.push(AppRoutes.clarification, extra: text);
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: VarSpacing.md,
        vertical: VarSpacing.sm,
      ),
      decoration: BoxDecoration(
        color: VarColors.bgSurfaceDark,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: VarColors.dividerDark),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _controller,
              style: VarTypography.body(16, VarColors.textPrimaryDark),
              decoration: InputDecoration(
                border: InputBorder.none,
                hintText: _examples[_exampleIndex],
                hintStyle: VarTypography.body(16, VarColors.textSecondaryDark),
              ),
              onSubmitted: (_) => _startClarification(),
            ),
          ),
          Semantics(
            button: true,
            label: 'Capturar por voz',
            child: IconButton(
              icon: const Icon(Icons.mic_none, color: VarColors.accentPrimary),
              onPressed: () => _showComingSoon('La captura de voz'),
            ),
          ),
        ],
      ),
    );
  }
}
