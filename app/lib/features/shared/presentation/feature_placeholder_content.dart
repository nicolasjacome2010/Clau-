import 'package:flutter/material.dart';

import '../../../design_system/var_spacing.dart';

/// Body content (no `Scaffold` of its own) for a nav destination that
/// exists in the shell (docs/UX_DESIGN.md Pantalla 4's bottom nav/rail:
/// Home, Mis Decisiones, Memoria, Perfil) but whose real screen is a
/// future module.
class FeaturePlaceholderContent extends StatelessWidget {
  const FeaturePlaceholderContent({super.key, required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(VarSpacing.lg),
        child: Text(
          '$label llega en un próximo módulo.',
          style: Theme.of(context).textTheme.bodyLarge,
          textAlign: TextAlign.center,
        ),
      ),
    );
  }
}
