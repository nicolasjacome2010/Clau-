import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../domain/settings_repository.dart';

/// Stores preferences in the platform's own key-value store.
///
/// The stored value is the enum's *name*, not its index: an index would
/// silently repoint every saved preference the day someone reorders
/// `ThemeMode`, and an unreadable value falls back to the default rather
/// than throwing on launch.
class PreferencesSettingsRepository implements SettingsRepository {
  PreferencesSettingsRepository({SharedPreferences? preferences})
    : _preferences = preferences;

  static const _themeModeKey = 'settings.theme_mode';

  SharedPreferences? _preferences;

  Future<SharedPreferences> get _prefs async =>
      _preferences ??= await SharedPreferences.getInstance();

  @override
  Future<ThemeMode> readThemeMode() async {
    final stored = (await _prefs).getString(_themeModeKey);
    for (final mode in ThemeMode.values) {
      if (mode.name == stored) return mode;
    }
    return ThemeMode.system;
  }

  @override
  Future<void> writeThemeMode(ThemeMode mode) async {
    await (await _prefs).setString(_themeModeKey, mode.name);
  }
}
