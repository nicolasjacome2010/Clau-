import 'package:shared_preferences/shared_preferences.dart';

import '../domain/pending_goals_store.dart';

/// Stores the pending goal queue in the platform's own key-value store —
/// same mechanism as `PreferencesSettingsRepository`, for the same reason:
/// this has to survive the app process ending, which the magic-link flow
/// makes routine rather than exceptional.
class PreferencesPendingGoalsStore implements PendingGoalsStore {
  PreferencesPendingGoalsStore({SharedPreferences? preferences})
    : _preferences = preferences;

  static const _pendingGoalsKey = 'onboarding.pending_goals';

  SharedPreferences? _preferences;

  Future<SharedPreferences> get _prefs async =>
      _preferences ??= await SharedPreferences.getInstance();

  @override
  Future<List<String>> read() async =>
      (await _prefs).getStringList(_pendingGoalsKey) ?? const [];

  @override
  Future<void> write(List<String> goalNames) async {
    final prefs = await _prefs;
    if (goalNames.isEmpty) {
      // Removing rather than storing an empty list keeps "nothing is owed"
      // as the absence of a key, so a stale empty list can never be
      // mistaken for state worth reading.
      await prefs.remove(_pendingGoalsKey);
      return;
    }
    await prefs.setStringList(_pendingGoalsKey, goalNames);
  }
}
