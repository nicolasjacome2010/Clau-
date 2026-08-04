import 'package:flutter/material.dart';

import '../../../design_system/var_spacing.dart';

/// Placeholder navigation target for Pantalla 4 ("El Mapa de Realidades",
/// docs/UX_DESIGN.md §2). Deliberately not the real Home screen — that's
/// its own future feature module (decision capture, active-decision cards,
/// bottom nav/rail). This exists only so `onboarding`/`auth` have somewhere
/// real to navigate to and can be tested end to end.
class HomePlaceholderScreen extends StatelessWidget {
  const HomePlaceholderScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(VarSpacing.lg),
          child: Text(
            'El Mapa de Realidades llega en el próximo módulo.',
            style: Theme.of(context).textTheme.bodyLarge,
            textAlign: TextAlign.center,
          ),
        ),
      ),
    );
  }
}
