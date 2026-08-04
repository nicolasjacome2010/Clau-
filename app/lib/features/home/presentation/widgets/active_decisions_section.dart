import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../design_system/var_colors.dart';
import '../../../../design_system/var_spacing.dart';
import '../../../../design_system/var_typography.dart';
import '../controllers/active_decisions_controller.dart';
import 'active_decision_card.dart';

class ActiveDecisionsSection extends ConsumerWidget {
  const ActiveDecisionsSection({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncDecisions = ref.watch(activeDecisionsControllerProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Decisiones activas',
          style: VarTypography.display(16, VarColors.textPrimaryDark),
        ),
        const SizedBox(height: VarSpacing.sm),
        SizedBox(
          height: 96,
          child: asyncDecisions.when(
            data: (decisions) => decisions.isEmpty
                ? Center(
                    child: Text(
                      'Aún no tienes decisiones activas.',
                      style: VarTypography.body(
                        14,
                        VarColors.textSecondaryDark,
                      ),
                    ),
                  )
                : ListView.builder(
                    scrollDirection: Axis.horizontal,
                    itemCount: decisions.length,
                    itemBuilder: (context, index) =>
                        ActiveDecisionCard(decision: decisions[index]),
                  ),
            loading: () => const Center(
              child: SizedBox(
                width: 24,
                height: 24,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
            ),
            error: (error, _) => _ActiveDecisionsError(
              onRetry: () => ref
                  .read(activeDecisionsControllerProvider.notifier)
                  .refresh(),
            ),
          ),
        ),
      ],
    );
  }
}

class _ActiveDecisionsError extends StatelessWidget {
  const _ActiveDecisionsError({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            'No pudimos cargar tus decisiones.',
            style: VarTypography.body(12, VarColors.signalLowDark),
          ),
          TextButton(onPressed: onRetry, child: const Text('Reintentar')),
        ],
      ),
    );
  }
}
