import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../design_system/var_palette.dart';
import '../../../../design_system/var_spacing.dart';
import '../../../../design_system/var_typography.dart';
import '../../domain/goal.dart';
import '../../domain/goal_option.dart';
import '../controllers/goals_controller.dart';
import 'goal_pill.dart';

/// Pantalla 13 — Perfil de Objetivos y Valores (docs/UX_DESIGN.md):
/// editable goal chips (the same seed set Onboarding offers), plus an
/// optional relative-weight slider per goal "oculto tras 'Ajuste avanzado'
/// para no abrumar por defecto" — so the advanced section starts collapsed
/// and the default view is just the chips.
class GoalsProfileTabContent extends ConsumerStatefulWidget {
  const GoalsProfileTabContent({super.key});

  @override
  ConsumerState<GoalsProfileTabContent> createState() =>
      _GoalsProfileTabContentState();
}

class _GoalsProfileTabContentState
    extends ConsumerState<GoalsProfileTabContent> {
  final _customGoalController = TextEditingController();
  bool _advancedExpanded = false;

  @override
  void dispose() {
    _customGoalController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final asyncGoals = ref.watch(goalsControllerProvider);
    final controller = ref.read(goalsControllerProvider.notifier);

    return asyncGoals.when(
      data: (goals) => ListView(
        padding: const EdgeInsets.all(VarSpacing.lg),
        children: [
          Text(
            'Tus objetivos',
            style: VarTypography.display(16, context.varColors.textPrimary),
          ),
          const SizedBox(height: VarSpacing.xs),
          Text(
            'Son la vara con la que cada escenario se compara.',
            style: VarTypography.body(12, context.varColors.textSecondary),
          ),
          const SizedBox(height: VarSpacing.md),
          if (goals.isEmpty)
            Text(
              'Aún no tienes objetivos. Añade al menos uno para que las simulaciones tengan con qué compararse.',
              style: VarTypography.body(14, context.varColors.textSecondary),
            )
          else
            Wrap(
              spacing: VarSpacing.sm,
              runSpacing: VarSpacing.sm,
              children: [
                for (final goal in goals)
                  GoalPill(
                    name: goal.name,
                    onRemove: () => controller.removeGoal(goal.id),
                  ),
              ],
            ),
          const SizedBox(height: VarSpacing.xl),
          _SuggestedGoals(goals: goals, onAdd: controller.addGoal),
          const SizedBox(height: VarSpacing.md),
          TextField(
            controller: _customGoalController,
            style: VarTypography.body(16, context.varColors.textPrimary),
            decoration: const InputDecoration(hintText: 'Otro objetivo…'),
            onSubmitted: (value) {
              controller.addGoal(value);
              _customGoalController.clear();
            },
          ),
          const SizedBox(height: VarSpacing.xl),
          if (goals.isNotEmpty)
            _AdvancedWeights(
              goals: goals,
              expanded: _advancedExpanded,
              onToggle: () =>
                  setState(() => _advancedExpanded = !_advancedExpanded),
              onWeightChanged: controller.setWeight,
            ),
        ],
      ),
      loading: () =>
          const Center(child: CircularProgressIndicator(strokeWidth: 2)),
      error: (error, _) => Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              'No pudimos cargar tus objetivos.',
              style: VarTypography.body(12, context.varColors.signalLow),
            ),
            TextButton(
              onPressed: controller.refresh,
              child: const Text('Reintentar'),
            ),
          ],
        ),
      ),
    );
  }
}

class _SuggestedGoals extends StatelessWidget {
  const _SuggestedGoals({required this.goals, required this.onAdd});

  final List<Goal> goals;
  final void Function(String name) onAdd;

  @override
  Widget build(BuildContext context) {
    final existing = goals.map((goal) => goal.name).toSet();
    final suggestions = GoalOption.seedOptions
        .where((option) => !existing.contains(option.label))
        .toList();
    if (suggestions.isEmpty) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Sugeridos',
          style: VarTypography.body(14, context.varColors.textSecondary),
        ),
        const SizedBox(height: VarSpacing.sm),
        Wrap(
          spacing: VarSpacing.sm,
          runSpacing: VarSpacing.sm,
          children: [
            for (final option in suggestions)
              ActionChip(
                label: Text(option.label),
                onPressed: () => onAdd(option.label),
              ),
          ],
        ),
      ],
    );
  }
}

class _AdvancedWeights extends StatefulWidget {
  const _AdvancedWeights({
    required this.goals,
    required this.expanded,
    required this.onToggle,
    required this.onWeightChanged,
  });

  final List<Goal> goals;
  final bool expanded;
  final VoidCallback onToggle;
  final void Function(String id, int weight) onWeightChanged;

  @override
  State<_AdvancedWeights> createState() => _AdvancedWeightsState();
}

class _AdvancedWeightsState extends State<_AdvancedWeights> {
  /// In-progress drag values, keyed by goal id. The slider can't read its
  /// position straight from `Goal.defaultWeight` while dragging — that only
  /// updates after the server round-trip, so the thumb would refuse to
  /// follow the finger. Cleared on release, once the stored value is the
  /// source of truth again.
  final Map<String, double> _dragging = {};

  @override
  Widget build(BuildContext context) {
    final goals = widget.goals;
    final expanded = widget.expanded;
    final onToggle = widget.onToggle;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextButton(
          onPressed: onToggle,
          child: Text(expanded ? 'Ocultar ajuste avanzado' : 'Ajuste avanzado'),
        ),
        if (expanded)
          for (final goal in goals) _weightRow(goal),
      ],
    );
  }

  Widget _weightRow(Goal goal) {
    final value = _dragging[goal.id] ?? goal.defaultWeight.toDouble();

    return Padding(
      padding: const EdgeInsets.only(bottom: VarSpacing.sm),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Text(
                  goal.name,
                  overflow: TextOverflow.ellipsis,
                  style: VarTypography.body(14, context.varColors.textPrimary),
                ),
              ),
              Text(
                '${value.round()}',
                style: VarTypography.mono(14, context.varColors.accentPrimary),
              ),
            ],
          ),
          Slider(
            value: value,
            max: 100,
            divisions: 20,
            label: '${value.round()}',
            onChanged: (next) => setState(() => _dragging[goal.id] = next),
            // Commits on release, not on every drag frame: one PATCH per
            // adjustment instead of dozens.
            onChangeEnd: (next) {
              setState(() => _dragging.remove(goal.id));
              widget.onWeightChanged(goal.id, next.round());
            },
          ),
        ],
      ),
    );
  }
}
