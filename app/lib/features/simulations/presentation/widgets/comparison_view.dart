import 'package:flutter/material.dart';

import '../../../../design_system/var_breakpoints.dart';
import '../../../../design_system/var_colors.dart';
import '../../../../design_system/var_spacing.dart';
import '../../../../design_system/var_typography.dart';
import '../../domain/simulation.dart';
import 'score_bar.dart';

/// Pantalla 8 — Resultado: Vista Comparación (docs/UX_DESIGN.md).
///
/// Two genuinely different layouts, not one squeezed into the other: a real
/// table on desktop/tablet ("tabla real en desktop — no cards forzadas a
/// tabla", for the analytical personas the spec names), and on mobile one
/// criterion per page with horizontal swipe between them.
///
/// **Alignment is one row per goal, never an average.** The wireframe shows
/// a single "Alineación objetivo" row, but a scenario carries a score per
/// goal and the client is not told how those goals are weighted against
/// each other (`GET /v1/decisions/{id}/simulations` returns the scores, not
/// the user's goal weights). Averaging them would invent an equal weighting
/// and present it as the system's opinion — so each goal gets its own row
/// and the user does the weighing, which is the product's whole posture.
class ComparisonView extends StatelessWidget {
  const ComparisonView({super.key, required this.scenarios});

  final List<SimulationScenario> scenarios;

  @override
  Widget build(BuildContext context) {
    final groups = _buildGroups(scenarios);
    final width = MediaQuery.sizeOf(context).width;

    if (VarBreakpoints.isMobile(width)) {
      return _SwipeableCriteria(groups: groups, scenarios: scenarios);
    }
    return _ComparisonTable(groups: groups, scenarios: scenarios);
  }
}

/// One row of the comparison: a label plus how to read each scenario's value
/// for it. `value` returns `null` when a scenario simply has no figure for
/// this criterion (a goal another scenario was scored against), which is
/// rendered as "—" rather than as a zero.
class _Criterion {
  const _Criterion({
    required this.label,
    required this.value,
    this.polarity = ScorePolarity.higherIsBetter,
  });

  final String label;
  final double? Function(SimulationScenario) value;
  final ScorePolarity polarity;
}

class _CriterionGroup {
  const _CriterionGroup({required this.title, required this.criteria});

  final String title;
  final List<_Criterion> criteria;
}

List<_CriterionGroup> _buildGroups(List<SimulationScenario> scenarios) {
  // Union across scenarios, in first-seen order: Reality Engine scores each
  // scenario against the goals it found relevant, so two scenarios need not
  // carry the same set.
  final goals = <String>[];
  for (final scenario in scenarios) {
    for (final alignment in scenario.goalAlignmentScores) {
      if (!goals.contains(alignment.goal)) goals.add(alignment.goal);
    }
  }

  return [
    if (goals.isNotEmpty)
      _CriterionGroup(
        title: 'Alineación',
        criteria: [
          for (final goal in goals)
            _Criterion(
              label: goal,
              value: (scenario) {
                for (final alignment in scenario.goalAlignmentScores) {
                  if (alignment.goal == goal) return alignment.score;
                }
                return null;
              },
            ),
        ],
      ),
    _CriterionGroup(
      title: 'Riesgo',
      criteria: [
        _Criterion(
          label: 'Riesgo',
          value: (scenario) => scenario.riskScore,
          polarity: ScorePolarity.lowerIsBetter,
        ),
      ],
    ),
    _CriterionGroup(
      title: 'Reversibilidad',
      criteria: [
        _Criterion(
          label: 'Reversibilidad',
          value: (scenario) => scenario.reversibilityScore,
        ),
      ],
    ),
    _CriterionGroup(
      title: 'Probabilidad',
      criteria: [
        _Criterion(
          label: 'Probabilidad relativa',
          value: (scenario) => scenario.relativeProbability,
          // Neither good nor bad news — see `ScorePolarity.neutral`.
          polarity: ScorePolarity.neutral,
        ),
      ],
    ),
  ];
}

/// Mobile: "cards apiladas por criterio (swipe horizontal entre criterios)".
class _SwipeableCriteria extends StatefulWidget {
  const _SwipeableCriteria({required this.groups, required this.scenarios});

  final List<_CriterionGroup> groups;
  final List<SimulationScenario> scenarios;

  @override
  State<_SwipeableCriteria> createState() => _SwipeableCriteriaState();
}

class _SwipeableCriteriaState extends State<_SwipeableCriteria> {
  final _controller = PageController();
  int _page = 0;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          // Tall enough for the busiest page (alignment, one bar per goal
          // per scenario) without clipping; each page scrolls on its own if
          // a large-text setting pushes past it.
          height: 320,
          child: PageView.builder(
            controller: _controller,
            itemCount: widget.groups.length,
            onPageChanged: (page) => setState(() => _page = page),
            itemBuilder: (context, index) {
              final group = widget.groups[index];
              return SingleChildScrollView(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      group.title,
                      style: VarTypography.display(
                        16,
                        VarColors.textPrimaryDark,
                      ),
                    ),
                    const SizedBox(height: VarSpacing.sm),
                    for (final criterion in group.criteria) ...[
                      if (group.criteria.length > 1)
                        Padding(
                          padding: const EdgeInsets.only(bottom: VarSpacing.xs),
                          child: Text(
                            criterion.label,
                            style: VarTypography.body(
                              12,
                              VarColors.textSecondaryDark,
                              weight: FontWeight.w600,
                            ),
                          ),
                        ),
                      for (final scenario in widget.scenarios)
                        _ScenarioValue(
                          label: scenario.title,
                          value: criterion.value(scenario),
                          polarity: criterion.polarity,
                        ),
                      const SizedBox(height: VarSpacing.sm),
                    ],
                  ],
                ),
              );
            },
          ),
        ),
        const SizedBox(height: VarSpacing.sm),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            for (var index = 0; index < widget.groups.length; index++)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 3),
                child: Container(
                  width: 6,
                  height: 6,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: index == _page
                        ? VarColors.accentPrimary
                        : VarColors.dividerDark,
                  ),
                ),
              ),
          ],
        ),
        const SizedBox(height: VarSpacing.xs),
        // The dots alone would leave a screen-reader user with no idea what
        // page they are on, and swiping is not discoverable without it.
        Center(
          child: Text(
            '${widget.groups[_page].title} · ${_page + 1} de ${widget.groups.length} · deslizá para ver más',
            textAlign: TextAlign.center,
            style: VarTypography.body(12, VarColors.textSecondaryDark),
          ),
        ),
      ],
    );
  }
}

class _ScenarioValue extends StatelessWidget {
  const _ScenarioValue({
    required this.label,
    required this.value,
    required this.polarity,
  });

  final String label;
  final double? value;
  final ScorePolarity polarity;

  @override
  Widget build(BuildContext context) {
    final score = value;
    if (score == null) return _MissingValue(label: label);
    return ScoreBar(label: label, score: score, polarity: polarity);
  }
}

/// A scenario that was never scored against this goal. Stated as absent
/// rather than drawn as a zero, which would read as "scores terribly".
class _MissingValue extends StatelessWidget {
  const _MissingValue({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: '$label: sin dato',
      child: Padding(
        padding: const EdgeInsets.only(bottom: VarSpacing.sm),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Expanded(
              child: Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: VarTypography.body(12, VarColors.textSecondaryDark),
              ),
            ),
            const SizedBox(width: VarSpacing.sm),
            Text(
              '—',
              style: VarTypography.mono(12, VarColors.textSecondaryDark),
            ),
          ],
        ),
      ),
    );
  }
}

/// Desktop/tablet: the spec's real table, one column per scenario.
class _ComparisonTable extends StatelessWidget {
  const _ComparisonTable({required this.groups, required this.scenarios});

  final List<_CriterionGroup> groups;
  final List<SimulationScenario> scenarios;

  @override
  Widget build(BuildContext context) {
    final criteria = [for (final group in groups) ...group.criteria];

    // Horizontal scroll rather than shrinking columns: with five scenarios
    // a squeezed table stops being readable, and the page itself must never
    // scroll sideways.
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Table(
        defaultColumnWidth: const FixedColumnWidth(200),
        columnWidths: const {0: FixedColumnWidth(180)},
        defaultVerticalAlignment: TableCellVerticalAlignment.middle,
        children: [
          TableRow(
            children: [
              _HeaderCell(
                text: 'Criterio',
                style: VarTypography.body(
                  12,
                  VarColors.textSecondaryDark,
                  weight: FontWeight.w600,
                ),
              ),
              for (final scenario in scenarios)
                _HeaderCell(
                  text: scenario.title,
                  style: VarTypography.display(
                    16,
                    scenario.isTopRanked
                        ? VarColors.accentPrimary
                        : VarColors.textPrimaryDark,
                  ),
                ),
            ],
          ),
          for (final criterion in criteria)
            TableRow(
              children: [
                _HeaderCell(
                  text: criterion.label,
                  style: VarTypography.body(12, VarColors.textSecondaryDark),
                ),
                for (final scenario in scenarios)
                  Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: VarSpacing.sm,
                      vertical: VarSpacing.xs,
                    ),
                    child: _ScenarioValue(
                      // The row already names the criterion, so the cell
                      // names the scenario — a screen reader reading a cell
                      // in isolation still knows whose number it is.
                      label: scenario.title,
                      value: criterion.value(scenario),
                      polarity: criterion.polarity,
                    ),
                  ),
              ],
            ),
        ],
      ),
    );
  }
}

class _HeaderCell extends StatelessWidget {
  const _HeaderCell({required this.text, required this.style});

  final String text;
  final TextStyle style;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: VarSpacing.sm,
        vertical: VarSpacing.sm,
      ),
      child: Text(text, style: style),
    );
  }
}
