import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/routing/app_router.dart';
import 'design_system/var_theme.dart';

void main() {
  runApp(const ProviderScope(child: VarOsApp()));
}

class VarOsApp extends ConsumerWidget {
  const VarOsApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(appRouterProvider);
    return MaterialApp.router(
      title: 'VAR OS',
      debugShowCheckedModeBanner: false,
      // Dark is the default, designed-first theme (docs/UX_DESIGN.md §4).
      themeMode: ThemeMode.dark,
      theme: VarTheme.light,
      darkTheme: VarTheme.dark,
      routerConfig: router,
    );
  }
}
