/// The six verticals `POST /v1/decisions` accepts (mirrors
/// `DecisionVertical` in backend/src/core_api/decisions/domain/entities.py).
///
/// Unlike `DecisionSummary.vertical`/`status` — raw wire strings, because
/// nothing in the app branches on their value — these need labels for the
/// clarification chips the user actually picks from, so the wire value and
/// its Spanish label are paired here in one place rather than scattered
/// across widgets.
class DecisionVerticalOption {
  const DecisionVerticalOption({required this.value, required this.label});

  final String value;
  final String label;

  static const all = [
    DecisionVerticalOption(value: 'career', label: 'Carrera'),
    DecisionVerticalOption(value: 'relationships', label: 'Relaciones'),
    DecisionVerticalOption(value: 'finance', label: 'Finanzas'),
    DecisionVerticalOption(value: 'business', label: 'Negocio'),
    DecisionVerticalOption(value: 'relocation', label: 'Mudanza'),
    DecisionVerticalOption(value: 'conflict', label: 'Conflicto'),
  ];
}
