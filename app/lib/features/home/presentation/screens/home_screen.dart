import 'package:flutter/material.dart';

import '../../../../design_system/var_breakpoints.dart';
import '../../../../design_system/var_colors.dart';
import '../../../decisions/presentation/widgets/my_decisions_tab_content.dart';
import '../../../goals/presentation/widgets/goals_profile_tab_content.dart';
import '../../../memory/presentation/widgets/memory_tab_content.dart';
import '../widgets/home_tab_content.dart';

/// Pantalla 4's nav shell: "Bottom nav (mobile) / rail lateral (tablet+):
/// Home, Mis Decisiones, Memoria, Perfil — 4 destinos máximo" — Home, Mis
/// Decisiones (Pantalla 10), Memoria (Pantalla 12) and Perfil (Pantalla 13
/// — Perfil de Objetivos) all have real content, so no destination is a
/// placeholder any more.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _tabIndex = 0;

  static const _destinations = [
    (label: 'Home', icon: Icons.home_outlined, selectedIcon: Icons.home),
    (
      label: 'Mis Decisiones',
      icon: Icons.list_alt_outlined,
      selectedIcon: Icons.list_alt,
    ),
    (
      label: 'Memoria',
      icon: Icons.auto_awesome_outlined,
      selectedIcon: Icons.auto_awesome,
    ),
    (label: 'Perfil', icon: Icons.person_outline, selectedIcon: Icons.person),
  ];

  static const _tabs = [
    HomeTabContent(),
    MyDecisionsTabContent(),
    MemoryTabContent(),
    GoalsProfileTabContent(),
  ];

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    final useRail = !VarBreakpoints.isMobile(width);
    final body = IndexedStack(index: _tabIndex, children: _tabs);

    return Scaffold(
      backgroundColor: VarColors.bgPrimaryDark,
      body: SafeArea(
        child: useRail
            ? Row(
                children: [
                  NavigationRail(
                    selectedIndex: _tabIndex,
                    onDestinationSelected: (index) =>
                        setState(() => _tabIndex = index),
                    labelType: NavigationRailLabelType.all,
                    destinations: [
                      for (final d in _destinations)
                        NavigationRailDestination(
                          icon: Icon(d.icon),
                          selectedIcon: Icon(d.selectedIcon),
                          label: Text(d.label),
                        ),
                    ],
                  ),
                  const VerticalDivider(width: 1, color: VarColors.dividerDark),
                  Expanded(child: body),
                ],
              )
            : body,
      ),
      bottomNavigationBar: useRail
          ? null
          : NavigationBar(
              selectedIndex: _tabIndex,
              onDestinationSelected: (index) =>
                  setState(() => _tabIndex = index),
              destinations: [
                for (final d in _destinations)
                  NavigationDestination(
                    icon: Icon(d.icon),
                    selectedIcon: Icon(d.selectedIcon),
                    label: d.label,
                  ),
              ],
            ),
    );
  }
}
