import 'package:flutter/material.dart';

/// Port for the handful of preferences that live on the device.
///
/// Appearance is deliberately *not* a server-side profile field: it is a
/// property of this device (a phone in dark mode at night and a desktop in
/// light mode by day are the same user), so syncing it would be wrong, not
/// just extra work.
abstract class SettingsRepository {
  Future<ThemeMode> readThemeMode();

  Future<void> writeThemeMode(ThemeMode mode);
}
