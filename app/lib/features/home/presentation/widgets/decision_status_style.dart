import 'package:flutter/material.dart';

import '../../../../design_system/var_colors.dart';

/// Maps a `DecisionSummary.status` to the left-border signal color and a
/// Spanish label (docs/UX_DESIGN.md Pantalla 4: "borde izquierdo de 3px con
/// el color de estado ... según qué tan cerca está de completarse, o gris
/// si es borrador"). Only active statuses reach this — `completed`/
/// `archived` decisions never appear in "Decisiones activas".
Color decisionStatusColor(String status) {
  switch (status) {
    case 'draft':
      return VarColors.dividerDark;
    case 'clarifying':
      return VarColors.signalLowDark;
    case 'simulating':
      return VarColors.signalMediumDark;
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
    default:
      return status;
  }
}
