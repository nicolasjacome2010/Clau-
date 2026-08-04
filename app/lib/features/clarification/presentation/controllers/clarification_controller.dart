import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../decisions/presentation/controllers/decisions_controller.dart';
import '../../domain/clarification_question.dart';
import '../../domain/raw_input_composer.dart';

enum ClarificationStatus { answering, submitting, created, failed }

class ClarificationState {
  const ClarificationState({
    this.questionIndex = 0,
    this.answers = const {},
    this.status = ClarificationStatus.answering,
    this.createdDecisionId,
    this.errorMessage,
  });

  final int questionIndex;
  final Map<String, String> answers;
  final ClarificationStatus status;
  final String? createdDecisionId;
  final String? errorMessage;

  ClarificationQuestion get currentQuestion =>
      ClarificationQuestion.all[questionIndex];

  int get remainingAfterCurrent =>
      ClarificationQuestion.all.length - questionIndex - 1;

  bool get isSubmitting => status == ClarificationStatus.submitting;

  ClarificationState copyWith({
    int? questionIndex,
    Map<String, String>? answers,
    ClarificationStatus? status,
    String? createdDecisionId,
    String? errorMessage,
  }) {
    return ClarificationState(
      questionIndex: questionIndex ?? this.questionIndex,
      answers: answers ?? this.answers,
      status: status ?? this.status,
      createdDecisionId: createdDecisionId ?? this.createdDecisionId,
      errorMessage: errorMessage,
    );
  }
}

/// Drives Pantalla 5: one chip question at a time, then creates the real
/// decision once every answer is in (`POST /v1/decisions`). Scoped per
/// screen via `.family` on the raw input, so re-entering with a different
/// decision text starts a clean flow instead of inheriting stale answers.
class ClarificationController
    extends FamilyNotifier<ClarificationState, String> {
  @override
  ClarificationState build(String rawInput) => const ClarificationState();

  Future<void> answerCurrent(String value) async {
    if (state.isSubmitting) return;

    final answers = {...state.answers, state.currentQuestion.id: value};
    if (state.remainingAfterCurrent > 0) {
      state = state.copyWith(
        questionIndex: state.questionIndex + 1,
        answers: answers,
      );
      return;
    }

    state = state.copyWith(
      answers: answers,
      status: ClarificationStatus.submitting,
    );
    await _createDecision(answers);
  }

  Future<void> retry() async {
    if (state.isSubmitting) return;
    state = state.copyWith(status: ClarificationStatus.submitting);
    await _createDecision(state.answers);
  }

  Future<void> _createDecision(Map<String, String> answers) async {
    final vertical = answers[ClarificationQuestion.verticalQuestionId];
    if (vertical == null) {
      // Unreachable while the vertical question is first and mandatory —
      // guarded rather than force-unwrapped so a future reordering fails
      // loudly here instead of sending a malformed request.
      state = state.copyWith(
        status: ClarificationStatus.failed,
        errorMessage: 'Falta el área de la decisión.',
      );
      return;
    }

    try {
      final id = await ref
          .read(decisionsRepositoryProvider)
          .createDecision(
            rawInput: composeRawInput(originalInput: arg, answers: answers),
            vertical: vertical,
          );
      // The new decision belongs in Home's "Decisiones activas" and in Mis
      // Decisiones immediately — both read the one shared controller, so a
      // single refresh updates both screens.
      await ref.read(decisionsControllerProvider.notifier).refresh();
      state = state.copyWith(
        status: ClarificationStatus.created,
        createdDecisionId: id,
      );
    } catch (error) {
      state = state.copyWith(
        status: ClarificationStatus.failed,
        errorMessage: 'No pudimos guardar tu decisión.',
      );
    }
  }
}

final clarificationControllerProvider =
    NotifierProvider.family<
      ClarificationController,
      ClarificationState,
      String
    >(ClarificationController.new);
