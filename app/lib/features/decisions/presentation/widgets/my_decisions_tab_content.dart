import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/routing/app_routes.dart';
import '../../../../design_system/var_colors.dart';
import '../../../../design_system/var_spacing.dart';
import '../../../../design_system/var_typography.dart';
import '../../domain/decision_ref.dart';
import '../../domain/decision_summary.dart';
import '../controllers/decisions_controller.dart';
import 'decision_status_style.dart';

/// Pantalla 10 — Mis Decisiones (docs/UX_DESIGN.md): a chronological list
/// grouped by "Activas / Completadas / Archivadas".
///
/// The spec also calls for a subtle ">60 días sin cerrar el ciclo"
/// indicator on completed items — deliberately not built here: no backend
/// endpoint currently exposes whether a `DecisionOutcome` already exists
/// for a given decision without an N+1 call per completed item (`POST
/// /v1/decisions/{id}/outcome` only *reports* one — there is no matching
/// GET to check first). A documented gap, not a missed detail; see
/// docs/PRD.md CU8 and backend/src/core_api/simulations/api/router.py.
class MyDecisionsTabContent extends ConsumerWidget {
  const MyDecisionsTabContent({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncDecisions = ref.watch(decisionsControllerProvider);

    return asyncDecisions.when(
      data: (decisions) {
        if (decisions.isEmpty) {
          return Center(
            child: Text(
              'Aún no tienes decisiones.',
              style: VarTypography.body(14, VarColors.textSecondaryDark),
            ),
          );
        }

        final active = decisions.where((d) => d.isActive).toList()
          ..sort(_byMostRecent);
        final completed = decisions.where((d) => d.isCompleted).toList()
          ..sort(_byMostRecent);
        final archived = decisions.where((d) => d.isArchived).toList()
          ..sort(_byMostRecent);

        return ListView(
          padding: const EdgeInsets.all(VarSpacing.lg),
          children: [
            if (active.isNotEmpty)
              _DecisionGroup(title: 'Activas', decisions: active),
            if (completed.isNotEmpty)
              _DecisionGroup(title: 'Completadas', decisions: completed),
            if (archived.isNotEmpty)
              _DecisionGroup(title: 'Archivadas', decisions: archived),
          ],
        );
      },
      loading: () =>
          const Center(child: CircularProgressIndicator(strokeWidth: 2)),
      error: (error, _) => Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              'No pudimos cargar tus decisiones.',
              style: VarTypography.body(12, VarColors.signalLowDark),
            ),
            TextButton(
              onPressed: () =>
                  ref.read(decisionsControllerProvider.notifier).refresh(),
              child: const Text('Reintentar'),
            ),
          ],
        ),
      ),
    );
  }
}

int _byMostRecent(DecisionSummary a, DecisionSummary b) =>
    b.updatedAt.compareTo(a.updatedAt);

class _DecisionGroup extends StatelessWidget {
  const _DecisionGroup({required this.title, required this.decisions});

  final String title;
  final List<DecisionSummary> decisions;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(
            bottom: VarSpacing.sm,
            top: VarSpacing.md,
          ),
          child: Text(
            title,
            style: VarTypography.display(16, VarColors.textPrimaryDark),
          ),
        ),
        for (final decision in decisions) _DecisionListTile(decision: decision),
      ],
    );
  }
}

class _DecisionListTile extends StatelessWidget {
  const _DecisionListTile({required this.decision});

  final DecisionSummary decision;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: '${decision.title}, ${decisionStatusLabel(decision.status)}',
      child: Container(
        margin: const EdgeInsets.only(bottom: VarSpacing.sm),
        // Surface color on `Material` so the ripple lands on the tile itself —
        // same reasoning as `ActiveDecisionCard`.
        child: Material(
          color: VarColors.bgSurfaceDark,
          borderRadius: BorderRadius.circular(12),
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            onTap: () => context.push(
              AppRoutes.decisionResult,
              extra: DecisionRef(id: decision.id, title: decision.title),
            ),
            child: Container(
              padding: const EdgeInsets.symmetric(
                horizontal: VarSpacing.md,
                vertical: VarSpacing.sm,
              ),
              decoration: BoxDecoration(
                border: Border(
                  left: BorderSide(
                    color: decisionStatusColor(decision.status),
                    width: 3,
                  ),
                ),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      decision.title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: VarTypography.body(
                        14,
                        VarColors.textPrimaryDark,
                        weight: FontWeight.w600,
                      ),
                    ),
                  ),
                  const SizedBox(width: VarSpacing.sm),
                  Text(
                    decisionStatusLabel(decision.status),
                    style: VarTypography.body(12, VarColors.textSecondaryDark),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
