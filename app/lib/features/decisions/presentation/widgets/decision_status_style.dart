import 'package:flutter/material.dart';

import '../../../../design_system/var_palette.dart';

/// Maps a `DecisionSummary.status` to a signal color and a Spanish label.
///
/// For active statuses this follows docs/UX_DESIGN.md Pantalla 4's "borde
/// izquierdo de 3px con el color de estado ... según qué tan cerca está de
/// completarse, o gris si es borrador". `completed`/`archived` (only shown
/// in Pantalla 10, "Mis Decisiones") extend the same scheme: `completed`
/// gets `signal.high` (fully resolved), `archived` stays neutral like
/// `draft` (no longer active, not a signal of anything).
/// Takes a `BuildContext` because the color it returns is theme-dependent
/// — the same status is a different hex in light and dark.
Color decisionStatusColor(BuildContext context, String status) {
  switch (status) {
    case 'draft':
      return context.varColors.divider;
    case 'clarifying':
      return context.varColors.signalLow;
    case 'simulating':
      return context.varColors.signalMedium;
    case 'completed':
      return context.varColors.signalHigh;
    case 'archived':
      return context.varColors.divider;
    default:
      return context.varColors.divider;
  }
}

String decisionStatusLabel(String status) {
  switch (status) {
    case 'draft':
      return 'Borrador';
    case 'clarifying':
      return 'Aclarando';
    case 'simulating':
      return 'Simulando';
    case 'completed':
      return 'Completada';
    case 'archived':
      return 'Archivada';
    default:
      return status;
  }
}
