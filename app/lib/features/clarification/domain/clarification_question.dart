import '../../decisions/domain/decision_vertical.dart';

class ClarificationOption {
  const ClarificationOption({required this.value, required this.label});

  /// What gets sent/recorded. For the vertical question this is the
  /// backend's own enum value; for context questions it's the label itself.
  final String value;
  final String label;
}

/// One guided question (docs/UX_DESIGN.md Pantalla 5). Deliberately
/// chip-only: the spec says the screen is "no es un chat de texto libre —
/// opciones de respuesta rápida (chips) siempre que sea posible", which
/// keeps the flow feeling like a structured instrument rather than a bot
/// conversation.
class ClarificationQuestion {
  const ClarificationQuestion({
    required this.id,
    required this.prompt,
    required this.options,
    required this.contextLabel,
  });

  final String id;
  final String prompt;
  final List<ClarificationOption> options;

  /// Prefix used when folding this answer into the decision's `raw_input`
  /// as extra context — `null` for `verticalQuestionId`, whose answer is a
  /// first-class API field rather than free context.
  final String? contextLabel;

  /// The question whose answer resolves `POST /v1/decisions`'s required
  /// `vertical`. Asking is the whole reason this screen runs before the
  /// decision is created — see `DecisionsRepository`'s docstring.
  static const verticalQuestionId = 'vertical';

  static final List<ClarificationQuestion> all = [
    ClarificationQuestion(
      id: verticalQuestionId,
      prompt: '¿De qué área es esta decisión?',
      contextLabel: null,
      options: [
        for (final vertical in DecisionVerticalOption.all)
          ClarificationOption(value: vertical.value, label: vertical.label),
      ],
    ),
    const ClarificationQuestion(
      id: 'timeframe',
      prompt: '¿Cuál es tu plazo para decidir?',
      contextLabel: 'Plazo para decidir',
      options: [
        ClarificationOption(value: 'Menos de 1 semana', label: '< 1 semana'),
        ClarificationOption(value: 'Entre 1 y 4 semanas', label: '1-4 semanas'),
        ClarificationOption(value: 'Sin plazo definido', label: 'Sin plazo'),
      ],
    ),
    const ClarificationQuestion(
      id: 'options_in_mind',
      prompt: '¿Ya tienes opciones concretas en mente?',
      contextLabel: 'Opciones concretas que ya considera',
      options: [
        ClarificationOption(value: 'Dos o más opciones', label: 'Dos o más'),
        ClarificationOption(value: 'Solo una opción', label: 'Solo una'),
        ClarificationOption(value: 'Ninguna todavía', label: 'Aún no'),
      ],
    ),
  ];
}
