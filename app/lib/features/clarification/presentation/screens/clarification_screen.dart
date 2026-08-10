import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../design_system/var_palette.dart';
import '../../../../design_system/var_motion.dart';
import '../../../../design_system/var_spacing.dart';
import '../../../../design_system/var_typography.dart';
import '../../../shared/presentation/step_indicator.dart';
import '../../domain/clarification_question.dart';
import '../controllers/clarification_controller.dart';
import '../widgets/answer_chip.dart';

/// Pantalla 5 — Clarificación (docs/UX_DESIGN.md §2): guided questions,
/// never a free chat. Runs between Home's capture field and the decision
/// actually existing: its first answer supplies the `vertical` that
/// `POST /v1/decisions` requires (see `DecisionsRepository`'s docstring).
///
/// Once the decision is created this pops back to Home rather than going
/// on to Pantalla 6 (Simulación en vivo): that screen streams pipeline
/// progress over a WebSocket the backend doesn't expose yet
/// (docs/ARCHITECTURE.md §2.2 describes it; `simulations` calls Reality
/// Engine synchronously with no progress channel). The decision lands in
/// "Decisiones activas" as a `draft`, which is truthful about where it is.
class ClarificationScreen extends ConsumerWidget {
  const ClarificationScreen({super.key, required this.rawInput});

  final String rawInput;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final provider = clarificationControllerProvider(rawInput);
    final state = ref.watch(provider);
    final controller = ref.read(provider.notifier);

    ref.listen(provider, (previous, next) {
      if (next.status == ClarificationStatus.created) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('Decisión guardada.')));
        context.pop();
      }
    });

    return Scaffold(
      backgroundColor: context.varColors.bgPrimary,
      appBar: AppBar(
        backgroundColor: context.varColors.bgPrimary,
        title: Text(
          'Entendiendo tu decisión…',
          style: VarTypography.body(16, context.varColors.textSecondary),
        ),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(VarSpacing.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Detecté que estás evaluando:',
                style: VarTypography.body(14, context.varColors.textSecondary),
              ),
              const SizedBox(height: VarSpacing.xs),
              Text(
                rawInput,
                style: VarTypography.display(20, context.varColors.textPrimary),
              ),
              const SizedBox(height: VarSpacing.xl),
              Expanded(
                child: state.isSubmitting
                    ? const Center(
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : _QuestionView(state: state, controller: controller),
              ),
              if (state.status == ClarificationStatus.failed) ...[
                Text(
                  state.errorMessage ?? 'Algo salió mal',
                  style: VarTypography.body(12, context.varColors.signalLow),
                ),
                TextButton(
                  onPressed: controller.retry,
                  child: const Text('Reintentar'),
                ),
              ],
              Center(
                child: StepIndicator(
                  stepCount: ClarificationQuestion.all.length,
                  currentStep: state.questionIndex,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _QuestionView extends StatelessWidget {
  const _QuestionView({required this.state, required this.controller});

  final ClarificationState state;
  final ClarificationController controller;

  @override
  Widget build(BuildContext context) {
    final question = state.currentQuestion;
    final remaining = state.remainingAfterCurrent;

    return AnimatedSwitcher(
      duration: VarMotion.screenTransitionMax,
      switchInCurve: VarMotion.enter,
      switchOutCurve: VarMotion.exit,
      // Scrollable because the chip `Wrap` grows to several rows on narrow
      // screens and with the OS "large text" setting (docs/UX_DESIGN.md
      // §1.5 requires that not to break the layout).
      child: SingleChildScrollView(
        key: ValueKey(question.id),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Antes de simular, necesito saber:',
              style: VarTypography.body(14, context.varColors.textSecondary),
            ),
            const SizedBox(height: VarSpacing.sm),
            Text(
              question.prompt,
              style: VarTypography.display(20, context.varColors.textPrimary),
            ),
            const SizedBox(height: VarSpacing.lg),
            Wrap(
              spacing: VarSpacing.sm,
              runSpacing: VarSpacing.sm,
              children: [
                for (final option in question.options)
                  AnswerChip(
                    label: option.label,
                    onTap: () => controller.answerCurrent(option.value),
                  ),
              ],
            ),
            const SizedBox(height: VarSpacing.md),
            if (remaining > 0)
              Text(
                remaining == 1 ? '1 pregunta más' : '$remaining preguntas más',
                style: VarTypography.body(12, context.varColors.textSecondary),
              ),
          ],
        ),
      ),
    );
  }
}
