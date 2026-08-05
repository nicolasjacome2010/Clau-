import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/preferences_settings_repository.dart';
import '../../domain/settings_repository.dart';

final settingsRepositoryProvider = Provider<SettingsRepository>(
  (ref) => PreferencesSettingsRepository(),
);

/// The app's theme mode, read from disk once and written on every change.
///
/// docs/UX_DESIGN.md Pantalla 15: "Dark/Light/System — default System pero
/// recomendando Dark en primer uso". The default is System because that is
/// what the spec says and because respecting the OS setting is the polite
/// default; the recommendation is copy on the setting itself, not a
/// pre-selected choice the user never made.
class ThemeModeController extends AsyncNotifier<ThemeMode> {
  @override
  Future<ThemeMode> build() =>
      ref.read(settingsRepositoryProvider).readThemeMode();

  Future<void> select(ThemeMode mode) async {
    // Applied immediately, then persisted: the switch must feel instant,
    // and a failed write costs a preference, not a broken screen.
    state = AsyncData(mode);
    await ref.read(settingsRepositoryProvider).writeThemeMode(mode);
  }
}

final themeModeControllerProvider =
    AsyncNotifierProvider<ThemeModeController, ThemeMode>(
      ThemeModeController.new,
    );
