import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'core/network/api_client.dart';
import 'core/routing/app_router.dart';
import 'design_system/var_theme.dart';
import 'features/auth/data/supabase_config.dart';
import 'features/auth/presentation/controllers/session_controller.dart';
import 'features/settings/presentation/controllers/settings_controller.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  if (isSupabaseConfigured) {
    // Restores a persisted session before the first frame, so a returning
    // user never sees a signed-out flash. Skipped entirely when the build
    // has no project — see `supabase_config.dart`.
    await Supabase.initialize(
      url: supabaseUrl,
      publishableKey: supabasePublishableKey,
    );
  }

  runApp(
    ProviderScope(
      overrides: [
        // The composition root is the one place allowed to know about both
        // sides: `core/` never imports a `features/` type, so the token
        // reaches the Dio interceptor by an override here rather than by an
        // upward import.
        accessTokenProvider.overrideWith(
          (ref) => ref.watch(sessionControllerProvider),
        ),
      ],
      child: const VarOsApp(),
    ),
  );
}

class VarOsApp extends ConsumerWidget {
  const VarOsApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(appRouterProvider);
    // Until the stored preference is read, dark: it is the designed-first
    // theme (docs/UX_DESIGN.md §4), so a returning user who chose dark never
    // sees a light flash on launch.
    final themeMode = ref.watch(themeModeControllerProvider).valueOrNull;
    return MaterialApp.router(
      title: 'VAR OS',
      debugShowCheckedModeBanner: false,
      themeMode: themeMode ?? ThemeMode.dark,
      theme: VarTheme.light,
      darkTheme: VarTheme.dark,
      routerConfig: router,
    );
  }
}
