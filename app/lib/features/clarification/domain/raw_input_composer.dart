import 'clarification_question.dart';

/// Folds the clarification answers into the decision's `raw_input`.
///
/// The backend's `CreateDecisionRequest` only carries `raw_input` and
/// `vertical` (backend/src/core_api/decisions/api/schemas.py), so the
/// non-vertical answers have nowhere else to go — and `raw_input` is
/// exactly what reaches Reality Engine's `/v1/simulate`, so this context
/// genuinely improves the simulation rather than being busywork.
///
/// The user's own words are never rewritten or interleaved: their text is
/// preserved verbatim and the answers are appended as a clearly delimited
/// block, so anyone reading a stored `raw_input` can tell exactly which
/// part the person wrote. Persisting these answers as their own columns
/// (docs/DATABASE.md has no table for them yet) is the cleaner long-term
/// shape and the documented next step.
String composeRawInput({
  required String originalInput,
  required Map<String, String> answers,
}) {
  final contextLines = <String>[];
  for (final question in ClarificationQuestion.all) {
    final label = question.contextLabel;
    final answer = answers[question.id];
    if (label == null || answer == null) continue;
    contextLines.add('- $label: $answer');
  }

  final trimmed = originalInput.trim();
  if (contextLines.isEmpty) return trimmed;
  return '$trimmed\n\nContexto de clarificación:\n${contextLines.join('\n')}';
}
