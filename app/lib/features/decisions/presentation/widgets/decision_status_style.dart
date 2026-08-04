import 'package:flutter/material.dart';

import '../../../../design_system/var_colors.dart';

/// Maps a `DecisionSummary.status` to a signal color and a Spanish label.
///
/// For active statuses this follows docs/UX_DESIGN.md Pantalla 4's "borde
/// izquierdo de 3px con el color de estado ... según qué tan cerca está de
/// completarse, o gris si es borrador". `completed`/`archived` (only shown
/// in Pantalla 10, "Mis Decisiones") extend the same scheme: `completed`
/// gets `signal.high` (fully resolved), `archived` stays neutral like
/// `draft` (no longer active, not a signal of anything).
Color decisionStatusColor(String status) {
  switch (status) {
    case 'draft':
      return VarColors.dividerDark;
    case 'clarifying':
      return VarColors.signalLowDark;
    case 'simulating':
      return VarColors.signalMediumDark;
    case 'completed':
      return VarColors.signalHighDark;
    case 'archived':
      return VarColors.dividerDark;
    default:
      return VarColors.dividerDark;
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
