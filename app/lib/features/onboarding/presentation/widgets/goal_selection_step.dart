import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../design_system/var_palette.dart';
import '../../../../design_system/var_spacing.dart';
import '../../../../design_system/var_typography.dart';
import '../../../goals/domain/goal_option.dart';
import '../controllers/onboarding_controller.dart';
import 'goal_chip.dart';

/// Paso 3 of Pantalla 2 (docs/UX_DESIGN.md): initial life-goal capture.
/// The selection reaches the backend's `goals` bounded context at the
/// first authenticated moment, not from here — see
/// `pending_goals_store.dart` for why that ordering is forced.
class GoalSelectionStep extends ConsumerStatefulWidget {
  const GoalSelectionStep({super.key});

  @override
  ConsumerState<GoalSelectionStep> createState() => _GoalSelectionStepState();
}

class _GoalSelectionStepState extends ConsumerState<GoalSelectionStep> {
  final _customGoalController = TextEditingController();

  @override
  void dispose() {
    _customGoalController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(onboardingControllerProvider);
    final controller = ref.read(onboardingControllerProvider.notifier);

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: VarSpacing.lg),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            '¿Qué te importa más ahora mismo?',
            textAlign: TextAlign.center,
            style: VarTypography.display(20, context.varColors.textPrimary),
          ),
          const SizedBox(height: VarSpacing.lg),
          Wrap(
            alignment: WrapAlignment.center,
            spacing: VarSpacing.sm,
            runSpacing: VarSpacing.sm,
            children: [
              for (final option in GoalOption.seedOptions)
                GoalChip(
                  label: option.label,
                  selected: state.selectedGoalIds.contains(option.id),
                  onTap: () => controller.toggleGoal(option.id),
                ),
              for (final custom in state.customGoals)
                GoalChip(label: custom, selected: true, onTap: () {}),
            ],
          ),
          const SizedBox(height: VarSpacing.lg),
          TextField(
            controller: _customGoalController,
            style: VarTypography.body(16, context.varColors.textPrimary),
            decoration: const InputDecoration(hintText: 'Otro objetivo…'),
            onSubmitted: (value) {
              controller.addCustomGoal(value);
              _customGoalController.clear();
            },
          ),
        ],
      ),
    );
  }
}
