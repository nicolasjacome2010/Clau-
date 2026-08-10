import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/routing/app_routes.dart';
import '../../../../design_system/var_palette.dart';
import '../../../../design_system/var_spacing.dart';
import '../../../../design_system/var_typography.dart';
import '../../../simulations/presentation/controllers/outcomes_controller.dart';
import '../../domain/decision_ref.dart';
import '../../domain/decision_summary.dart';
import '../controllers/decisions_controller.dart';
import 'decision_status_style.dart';

/// Pantalla 10 — Mis Decisiones (docs/UX_DESIGN.md): a chronological list
/// grouped by "Activas / Completadas / Archivadas", with the spec's subtle
/// "sin cerrar el ciclo" marker on completed decisions left open for more
/// than 60 days.
///
/// That marker reads the one shared `GET /v1/outcomes` response
/// (`decisionOutcomeProvider`), never a request per row — the endpoint is a
/// collection precisely so this screen costs one call, not fifty.
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
              style: VarTypography.body(14, context.varColors.textSecondary),
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
              style: VarTypography.body(12, context.varColors.signalLow),
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
            style: VarTypography.display(16, context.varColors.textPrimary),
          ),
        ),
        for (final decision in decisions) _DecisionListTile(decision: decision),
      ],
    );
  }
}

/// docs/UX_DESIGN.md Pantalla 10: "un indicador sutil de 'sin cerrar el
/// ciclo' (punto ámbar) si pasaron >60 días sin reportar resultado real —
/// invita, no presiona".
const _openLoopAfter = Duration(days: 60);

class _DecisionListTile extends ConsumerWidget {
  const _DecisionListTile({required this.decision});

  final DecisionSummary decision;

  /// Only completed decisions can have a loop to close (`POST
  /// .../outcome` answers 409 otherwise), and only after the spec's 60
  /// days does an open one deserve a mark at all.
  bool _isOpenLoop(WidgetRef ref) {
    if (!decision.isCompleted) return false;
    if (DateTime.now().difference(decision.updatedAt) < _openLoopAfter) {
      return false;
    }
    return ref.watch(decisionOutcomeProvider(decision.id)) == null;
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isOpenLoop = _isOpenLoop(ref);

    return Semantics(
      button: true,
      label:
          '${decision.title}, ${decisionStatusLabel(decision.status)}'
          '${isOpenLoop ? ', sin cerrar el ciclo' : ''}',
      child: Container(
        margin: const EdgeInsets.only(bottom: VarSpacing.sm),
        // Surface color on `Material` so the ripple lands on the tile itself —
        // same reasoning as `ActiveDecisionCard`.
        child: Material(
          color: context.varColors.bgSurface,
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
                    color: decisionStatusColor(context, decision.status),
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
                        context.varColors.textPrimary,
                        weight: FontWeight.w600,
                      ),
                    ),
                  ),
                  const SizedBox(width: VarSpacing.sm),
                  if (isOpenLoop) const _OpenLoopMarker(),
                  Text(
                    decisionStatusLabel(decision.status),
                    style: VarTypography.body(
                      12,
                      context.varColors.textSecondary,
                    ),
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

/// The amber dot the spec asks for — plus the words, because
/// docs/UX_DESIGN.md §1.5 forbids color as the only carrier of meaning, and
/// a lone dot would be unreadable to anyone who can't distinguish it.
///
/// Phrased as a state ("sin cerrar"), never as a demand: the spec's own
/// "invita, no presiona" rules out a badge, a count, or a call to action.
class _OpenLoopMarker extends StatelessWidget {
  const _OpenLoopMarker();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(right: VarSpacing.sm),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 6,
            height: 6,
            decoration: BoxDecoration(
              color: context.varColors.signalMedium,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: VarSpacing.xs),
          Text(
            'Sin cerrar',
            style: VarTypography.body(12, context.varColors.signalMedium),
          ),
        ],
      ),
    );
  }
}
